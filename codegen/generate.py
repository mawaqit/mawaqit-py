"""Generate the models, resources and clients from the OpenAPI spec.

Usage:
    uv run --group codegen codegen/generate.py                 # pinned spec, via gh
    uv run --group codegen codegen/generate.py --spec-dir DIR  # a checkout of it
    uv run --group codegen codegen/generate.py --pin v0.2.0    # pin another tag

The spec lives in the private mawaqit/api-spec repository, pinned by tag and
SHA-256 in codegen/spec.json; only `--pin` changes the pin. Its examples, real
API responses, are copied to tests/examples.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import subprocess
import sys
import tarfile
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "src" / "mawaqit"
RESOURCES = PACKAGE / "resources"
# Real API responses, kept for the tests.
EXAMPLES = ROOT / "tests" / "examples"
PIN = Path(__file__).with_name("spec.json")
TEMPLATES = Path(__file__).with_name("templates")
WIDTH = 88

# The exception raised for each documented error status.
ERRORS = {
    400: "BadRequestError",
    401: "AuthenticationError",
    403: "PermissionDeniedError",
    404: "NotFoundError",
    429: "RateLimitError",
}
BASIC_AUTH_ARGS = {
    "email": "Email of the MAWAQIT account.",
    "password": "Password of the MAWAQIT account.",
}
LITERALS = {"null": "None", "true": "True", "false": "False"}


def is_empty_array(schema: object) -> bool:
    """Whether a schema is `[]`, the API's answer for nothing, returned as `None`."""
    return (
        isinstance(schema, dict)
        and schema.get("type") == "array"
        and schema.get("maxItems") == 0
    )


def snake(name: str) -> str:
    """Return a camelCase name in snake_case: `hijriDateForceTo30` gives `..._to_30`."""
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Za-z])(?=[0-9])", "_", name).lower()


class SpecError(Exception):
    """The spec uses something the generator does not support."""


@dataclass
class Field:
    """A field of a model."""

    name: str
    alias: str | None
    type: str
    required: bool
    deprecated: str | None
    sensitive: bool
    doc: str


@dataclass
class Model:
    """A model, from a schema of the components."""

    name: str
    doc: str
    fields: list[Field]
    refs: set[str]


@dataclass
class Param:
    """A parameter of an operation."""

    name: str
    wire_name: str
    type: str
    required: bool
    doc: str


@dataclass
class Operation:
    """An operation, which becomes a method of its resource."""

    name: str
    method: str
    path: str
    doc: str
    returns: str
    adapter: str
    refs: set[str] = field(default_factory=set)
    path_params: list[Param] = field(default_factory=list)
    query_params: list[Param] = field(default_factory=list)
    basic_auth: bool = False
    authenticated: bool = True
    empty_as_none: bool = False

    @property
    def signature(self) -> str:
        """The parameters of the method: path ones first, the others by keyword."""
        params = ["self", *(f"{p.name}: {p.type}" for p in self.path_params)]
        keywords = [
            f"{p.name}: {p.type}" + ("" if p.required else " | None = None")
            for p in self.query_params
        ]
        if self.basic_auth:
            keywords += ["email: str", "password: str"]
        return ", ".join(params + (["*", *keywords] if keywords else []))

    @property
    def call(self) -> str:
        """The arguments of the request of the method."""
        args = [repr(self.method).replace("'", '"'), f'"{self.path}"']
        if self.path_params:
            items = ", ".join(f'"{p.wire_name}": {p.name}' for p in self.path_params)
            args.append(f"path_params={{{items}}}")
        if self.query_params:
            items = ", ".join(f'"{p.wire_name}": {p.name}' for p in self.query_params)
            args.append(f"params={{{items}}}")
        if self.basic_auth:
            args.append("basic_auth=(email, password)")
        if not self.authenticated:
            args.append("authenticated=False")
        if self.empty_as_none:
            args.append("empty_as_none=True")
        args.append(f"response_type={self.adapter}")
        return ", ".join(args)


@dataclass
class Resource:
    """A resource: the operations of a tag."""

    name: str
    module: str
    doc: str
    operations: list[Operation] = field(default_factory=list)
    types: set[str] = field(default_factory=set)


class Generator:
    """Turns the spec into the data the templates render."""

    def __init__(self, spec: dict[str, Any]) -> None:
        """Index the names of the spec, to translate them in descriptions."""
        self.spec = spec
        self.schemas: dict[str, Any] = spec["components"]["schemas"]
        # Every name a description can quote, to translate it to Python.
        self.names: dict[str, str] = {}
        for schema in self.schemas.values():
            for prop in schema.get("properties", {}):
                self.names[prop] = snake(prop)
        for item in spec["paths"].values():
            for operation in item.values():
                for param in self._parameters(operation):
                    self.names[param["name"]] = snake(param["name"])
                tag = operation["tags"][0]
                method = snake(operation["operationId"].removeprefix(tag))
                self.names[operation["operationId"]] = f"client.{tag}.{method}()"

    # Text

    def pythonize(self, text: str) -> str:
        """Translate the names quoted in a description to their Python names."""

        def replace(match: re.Match[str]) -> str:
            word = match.group(1)
            return f"`{LITERALS.get(word) or self.names.get(word) or word}`"

        return re.sub(r"`([^`]+)`", replace, " ".join(text.split()))

    def paragraphs(self, text: str | None) -> list[str]:
        """Return the paragraphs of a description, in Python terms."""
        if not text:
            return []
        return [self.pythonize(p) for p in re.split(r"\n\s*\n", text.strip())]

    @staticmethod
    def first_sentence(text: str) -> str:
        """Return the first sentence of a text."""
        return re.split(r"(?<=\.) ", text, maxsplit=1)[0]

    def docstring(
        self,
        summary: str,
        body: list[str],
        indent: int,
        sections: Mapping[str, Sequence[tuple[str | None, str]]] | None = None,
    ) -> str:
        """Return a Google style docstring, without its quotes."""
        pad = " " * indent
        lines = [summary]
        for paragraph in body:
            lines += [
                "",
                textwrap.fill(
                    paragraph, WIDTH, initial_indent=pad, subsequent_indent=pad
                ),
            ]
        for title, entries in (sections or {}).items():
            if not entries:
                continue
            lines += ["", f"{pad}{title}:"]
            for name, text in entries:
                entry = f"{name}: {text}" if name else text
                lines.append(
                    textwrap.fill(
                        entry,
                        WIDTH,
                        initial_indent=pad + "    ",
                        subsequent_indent=pad + "        ",
                    )
                )
        if len(lines) > 1:
            lines.append(pad)
        return "\n".join(lines).replace(pad + "\n", "\n")

    def attribute_doc(self, text: str) -> str:
        """Return the docstring of a model field, without its quotes."""
        paragraphs = self.paragraphs(text)
        pad = "    "
        if len(paragraphs) == 1 and len(paragraphs[0]) + len(pad) + 6 <= WIDTH:
            return paragraphs[0]
        # The first line starts after the opening quotes.
        first = pad + '"""'
        filled = [
            textwrap.fill(
                paragraphs[0], WIDTH, initial_indent=first, subsequent_indent=pad
            ).removeprefix(first),
            *(
                textwrap.fill(p, WIDTH, initial_indent=pad, subsequent_indent=pad)
                for p in paragraphs[1:]
            ),
        ]
        return "\n\n".join(filled) + "\n" + pad

    def summary_and_body(self, text: str) -> tuple[str, list[str]]:
        """Split a description into a summary line and paragraphs."""
        paragraphs = self.paragraphs(text)
        summary = self.first_sentence(paragraphs[0])
        rest = paragraphs[0].removeprefix(summary).strip()
        return summary, ([rest] if rest else []) + paragraphs[1:]

    # Types

    def python_type(self, schema: dict[str, Any], refs: set[str]) -> str:
        """Return the annotation of a schema, collecting the models it uses."""
        if "$ref" in schema:
            name = str(schema["$ref"]).removeprefix("#/components/schemas/")
            refs.add(name)
            return name
        if "anyOf" in schema:
            # Only `anyOf: [X, {type: "null"}]`, for a nullable reference, or
            # `anyOf: [X, []]`, whose empty array the client returns as `None`.
            match schema["anyOf"]:
                case [other, nullable] if "$ref" in other and (
                    nullable == {"type": "null"} or is_empty_array(nullable)
                ):
                    return f"{self.python_type(other, refs)} | None"
                case _:
                    raise SpecError(f"unsupported anyOf {schema['anyOf']!r}")
        types = schema.get("type")
        types = [types] if isinstance(types, str) else list(types or [])
        nullable = "null" in types
        types = [t for t in types if t != "null"]
        if len(types) != 1:
            raise SpecError(f"unsupported type {schema.get('type')!r}")
        kind = types[0]
        if kind == "array":
            annotation = f"list[{self.python_type(schema['items'], refs)}]"
        elif kind == "object":
            if schema.get("properties") or "additionalProperties" not in schema:
                raise SpecError("objects with properties must be components")
            value = self.python_type(schema["additionalProperties"], refs)
            annotation = f"dict[str, {value}]"
        elif kind == "string":
            formats = {"date": "date", "date-time": "datetime"}
            annotation = formats.get(schema.get("format", ""), "str")
        else:
            annotation = {"integer": "int", "number": "float", "boolean": "bool"}[kind]
        return f"{annotation} | None" if nullable else annotation

    def models(self) -> list[Model]:
        """Return the models of the schemas the operations return."""
        models: dict[str, Model] = {}
        for name, schema in self.schemas.items():
            if schema.get("type") != "object" or "properties" not in schema:
                raise SpecError(f"{name}: only object schemas can be components")
            refs: set[str] = set()
            fields = []
            required = set(schema.get("required", []))
            for prop, prop_schema in schema["properties"].items():
                annotation = self.python_type(prop_schema, refs)
                if prop not in required and not annotation.endswith("| None"):
                    annotation += " | None"
                fields.append(
                    Field(
                        name=snake(prop),
                        alias=None if snake(prop) == prop else prop,
                        type=annotation,
                        required=prop in required,
                        deprecated=self._deprecation(prop, prop_schema),
                        sensitive=prop_schema.get("x-sensitive", False),
                        doc=self.attribute_doc(self._description(prop_schema)),
                    )
                )
            summary, body = self.summary_and_body(schema["description"])
            doc = self.docstring(summary, body, indent=4)
            models[name] = Model(name, doc, fields, refs)
        return self._dependencies_first(models)

    def _deprecation(self, name: str, schema: dict[str, Any]) -> str | None:
        """Return the warning of a deprecated property, with its replacement."""
        if not schema.get("deprecated"):
            return None
        sentences = re.split(r"(?<=\.) ", self.pythonize(schema["description"]))
        advice = [s for s in sentences if s.startswith("Use ")]
        return " ".join([f"{snake(name)} is deprecated.", *advice])

    def _description(self, schema: dict[str, Any]) -> str:
        """Return the description of a schema, or of the one it refers to."""
        if "description" in schema:
            return str(schema["description"])
        return str(self._resolve(schema)["description"])

    def _dependencies_first(self, models: dict[str, Model]) -> list[Model]:
        """Return the models the operations return, each after those it uses."""
        ordered: dict[str, Model] = {}

        def visit(model: Model) -> None:
            for ref in sorted(model.refs):
                if ref not in ordered:
                    visit(models[ref])
            ordered.setdefault(model.name, model)

        returned: set[str] = set()
        for resource in self.resources():
            for operation in resource.operations:
                returned |= operation.refs
        for model in models.values():
            if model.name in returned:
                visit(model)
        return list(ordered.values())

    # Operations

    def _parameters(self, operation: dict[str, Any]) -> list[dict[str, Any]]:
        return [self._resolve(p) for p in operation.get("parameters", [])]

    def _resolve(self, node: dict[str, Any]) -> dict[str, Any]:
        if "$ref" not in node:
            return node
        target: Any = self.spec
        for part in node["$ref"].removeprefix("#/").split("/"):
            target = target[part]
        return target  # type: ignore[no-any-return]

    def _param(self, param: dict[str, Any], refs: set[str]) -> Param:
        schema = param["schema"]
        notes = []
        if "minimum" in schema and "maximum" in schema:
            notes.append(f"From {schema['minimum']} to {schema['maximum']}")
        elif "minimum" in schema:
            notes.append(f"At least {schema['minimum']}")
        if "default" in schema:
            default = schema["default"]
            value = f"`{default}`" if isinstance(default, str) else default
            notes.append(f"{value} by default")
        doc = self.pythonize(param["description"])
        if notes:
            doc += " " + ", ".join(notes) + "."
        return Param(
            name=snake(param["name"]),
            wire_name=param["name"],
            type=self.python_type(schema, refs).removesuffix(" | None"),
            required=param.get("required", False),
            doc=doc,
        )

    def resources(self) -> list[Resource]:
        """Return the resources, one per tag, with their operations."""
        tags = {tag["name"]: tag for tag in self.spec["tags"]}
        resources = {
            name: Resource(
                name=name.title(),
                module=name,
                doc=self.pythonize(tag["description"]),
            )
            for name, tag in tags.items()
        }
        default_security = self.spec.get("security", [])
        for path, item in self.spec["paths"].items():
            for method, operation in item.items():
                tag = operation["tags"][0]
                operation_id = operation["operationId"]
                if not operation_id.startswith(tag):
                    raise SpecError(f"{operation_id} does not start with its tag {tag}")
                resource = resources[tag]
                refs: set[str] = set()
                schemes = {
                    scheme
                    for requirement in operation.get("security", default_security)
                    for scheme in requirement
                }
                schema = operation["responses"]["200"]["content"]["application/json"]
                returns = self.python_type(schema["schema"], refs)
                params = [self._param(p, refs) for p in self._parameters(operation)]
                name = snake(operation_id.removeprefix(tag))
                summary, body = (
                    operation["summary"] + ".",
                    self.paragraphs(operation["description"]),
                )
                args = [(p.name, p.doc) for p in params if p.wire_name in path]
                args += [(p.name, p.doc) for p in params if p.wire_name not in path]
                basic_auth = "basicAuth" in schemes
                if basic_auth:
                    args += list(BASIC_AUTH_ARGS.items())
                raises = [
                    (
                        ERRORS[int(status)],
                        self.first_sentence(
                            self.pythonize(self._resolve(response)["description"])
                        ),
                    )
                    for status, response in operation["responses"].items()
                    if status != "200"
                ]
                raises.append(("APIError", "The request failed in another way."))
                response_doc = self.pythonize(
                    operation["responses"]["200"]["description"]
                )
                doc = self.docstring(
                    summary,
                    body,
                    indent=8,
                    sections={
                        "Args": args,
                        "Returns": [(None, response_doc)],
                        "Raises": raises,
                    },
                )
                resource.operations.append(
                    Operation(
                        name=name,
                        method=method.upper(),
                        path=path,
                        doc=doc,
                        returns=returns,
                        adapter=f"_{name.upper()}",
                        refs=refs,
                        path_params=[p for p in params if p.wire_name in path],
                        query_params=[p for p in params if p.wire_name not in path],
                        basic_auth=basic_auth,
                        authenticated="apiToken" in schemes,
                        empty_as_none=is_empty_array(
                            schema["schema"].get("anyOf", [None, None])[1]
                        ),
                    )
                )
                resource.types |= refs
        return list(resources.values())


def load_pin() -> dict[str, str]:
    """Return the pinned spec: repository, ref, path and SHA-256."""
    return json.loads(PIN.read_text())  # type: ignore[no-any-return]


def download(repository: str, ref: str) -> dict[str, bytes]:
    """Return the files of a tag of a private repository, with the GitHub CLI."""
    try:
        archive = subprocess.run(
            ["gh", "api", f"repos/{repository}/tarball/{ref}"],
            check=True,
            capture_output=True,
        ).stdout
    except FileNotFoundError:
        sys.exit("Install the GitHub CLI (gh), or pass --spec-dir.")
    except subprocess.CalledProcessError as err:
        sys.exit(f"Could not download the spec: {err.stderr.decode().strip()}")
    files = {}
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        for member in tar.getmembers():
            content = tar.extractfile(member) if member.isfile() else None
            if content:
                # Paths start with a directory named after the commit.
                files[member.name.split("/", 1)[1]] = content.read()
    return files


def read_checkout(root: Path) -> dict[str, bytes]:
    """Return the files of a checkout of the spec repository."""
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for folder in ("openapi", "examples")
        for path in (root / folder).rglob("*")
        if path.is_file()
    }


def render(spec: dict[str, Any], pin: dict[str, str]) -> dict[Path, str]:
    """Return the generated files and their content."""
    generator = Generator(spec)
    # Renders Python code, not HTML.
    env = Environment(  # noqa: S701
        loader=FileSystemLoader(TEMPLATES),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    header = (
        f"# Generated by codegen/generate.py from {pin['repository']} "
        f"{pin['ref']}. Do not edit."
    )
    resources = generator.resources()
    files = {
        PACKAGE / "types.py": env.get_template("types.py.jinja").render(
            header=header, models=generator.models()
        ),
        PACKAGE / "_client.py": env.get_template("client.py.jinja").render(
            header=header, resources=resources
        ),
        PACKAGE / "resources" / "__init__.py": env.get_template(
            "resources_init.py.jinja"
        ).render(header=header, resources=resources),
    }
    for resource in resources:
        files[PACKAGE / "resources" / f"{resource.module}.py"] = env.get_template(
            "resource.py.jinja"
        ).render(header=header, resource=resource)
    return files


def write(files: dict[Path, str | bytes], *, prune: Path | None = None) -> None:
    """Write files, and delete the other files of the folder to prune."""
    for stale in prune.rglob("*") if prune else ():
        if stale.is_file() and stale not in files:
            stale.unlink()
    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, str):
            path.write_text(content)
        else:
            path.write_bytes(content)


def main() -> None:
    """Generate the code from the pinned spec, or from --spec-dir or --pin."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--spec-dir", type=Path, help="read the spec from this checkout of it"
    )
    source.add_argument("--pin", metavar="REF", help="pin this tag of the spec")
    args = parser.parse_args()

    pin = load_pin()
    if args.pin:
        pin["ref"] = args.pin
    spec_files = (
        read_checkout(args.spec_dir)
        if args.spec_dir
        else download(pin["repository"], pin["ref"])
    )
    content = spec_files[pin["path"]]
    digest = hashlib.sha256(content).hexdigest()
    if args.pin:
        pin["sha256"] = digest
        PIN.write_text(json.dumps(pin, indent=2) + "\n")
    elif digest != pin["sha256"]:
        sys.exit(
            f"The spec differs from {pin['repository']} {pin['ref']}: "
            "pin it with --pin instead."
        )

    code = render(yaml.safe_load(content), pin)
    # Unlike the rest of the package, the resources are all generated.
    write({p: c for p, c in code.items() if p.parent != RESOURCES})
    write({p: c for p, c in code.items() if p.parent == RESOURCES}, prune=RESOURCES)
    paths = [str(path) for path in code]
    # Format first: lint would flag the long lines that formatting wraps.
    subprocess.run(["ruff", "format", "--quiet", *paths], check=True)
    subprocess.run(["ruff", "check", "--fix", "--quiet", *paths], check=True)
    subprocess.run(["ruff", "format", "--quiet", *paths], check=True)

    examples = {
        EXAMPLES / path.removeprefix("examples/"): data
        for path, data in spec_files.items()
        if path.startswith("examples/") and path.endswith(".json")
    }
    write(dict(examples), prune=EXAMPLES)
    print(
        f"Generated {len(code)} files and {len(examples)} examples "
        f"from {pin['repository']} {pin['ref']}."
    )


if __name__ == "__main__":
    main()
