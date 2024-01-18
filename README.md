# MAWAQIT Python Library

‏السلام عليكم ورحمة الله وبركاته

This is the official Python library to access the [MAWAQIT](https://mawaqit.net) API.

## Installation

To use this Python library, you can install it via pip:

```bash
pip install mawaqit-py
```

## Usage

### Synchroneous version

`TODO`

### Asynchroneous version

Here's a simple example of how to use this library:

```python
from mawaqit_async import MawaqitClient

# Initialize the Mawaqit client:
# You can pass the username and password as parameters,
# or directly your valid MAWAQIT API token
# You can also pass your location (latitude and longitude) as parameters to get the nearest mosques
client = MawaqitClient(username=USERNAME,
                       password=PASSWORD,
                       latitude=LATITUDE,
                       longitude=LONGITUDE)

# Example: Fetch the API token
api_token = await client.get_api_token()

# Example: Get information about the five nearest mosques
nearest_mosques = await client.all_mosques_neighborhood()

# Example: Fetch prayer times for a specific mosque
prayer_times = await client.fetch_prayer_times()
```

## Exceptions

- `NotAuthenticatedException`: Raised when authentication fails.
- `BadCredentialsException`: Raised when login credentials are incorrect.
- `NoMosqueAround`: Raised when no mosques are found around the specified location.
- `MissingCredentials`: Raised when required credentials are not provided.


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


## Contributing

If you want to contribute to this project, feel free to [fork](https://github.com/mawaqit/mawaqit-py/fork) it and submit a pull request.

You can also open an [issue](https://github.com/mawaqit/mawaqit-py/issues/new) if you find any bug or have any suggestion.


## Questions

If you have any question, feel free to contact us at [support@mawaqit.net](mailto:support@mawaqit.net).


## May Allah reward you!





