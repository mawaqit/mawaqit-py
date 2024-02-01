# MAWAQIT Python Library

‏السلام عليكم ورحمة الله وبركاته

This is the official Python library to access the [MAWAQIT](https://mawaqit.net) API.

## Installation

To use this Python library, you can install it via pip:

```bash
pip install mawaqit
```

## Usage

### Synchroneous version

`TODO : Not made yet.`

### Asynchroneous version

Here's a simple example (with asyncio) on how to use this library.
You can check the [async_example.py](examples/async_example.py) file to copy this code.

```python
import asyncio
from mawaqit import AsyncMawaqitClient


async def main():
    # Initialize the Mawaqit client:
    # You can pass the username and password as parameters,
    # or directly your valid MAWAQIT API token
    # You can also pass your location (latitude and longitude) as parameters to get the nearest mosques
    client = AsyncMawaqitClient(username=USERNAME,
                                password=PASSWORD,
                                longitude=LONGITUDE,
                                latitude=LATITUDE)
    
    # Get your API token
    api_token = await client.get_api_token()

    # Get information of the 5 nearest mosques around the given position (long, lat)
    mosques = await client.all_mosques_neighborhood()
    
    # Set the mosque to use
    client.mosque = mosques[0]['uuid']
    
    # Fetch the prayer times from client.mosque
    print(client.fetch_prayer_times())
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
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





