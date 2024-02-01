import asyncio
from mawaqit import AsyncMawaqitClient


USERNAME = "YOUR_USERNAME"
PASSWORD = "YOUR_PASSWORD"
LONGITUDE = 0
LATITUDE = 0


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
