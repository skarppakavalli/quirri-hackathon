
import asyncio

from backend.services.request_parser import RequestParser


def test_request_parser():

    async def run_test():

        parser = RequestParser()

        messages = [
            "I need medical leave tomorrow because I am unwell.",
            "I need OD tomorrow to attend a hackathon.",
            "I need leave next Monday for personal work.",
            "I want leave."
        ]

        for message in messages:

            print("\nStudent:", message)

            result = await parser.parse_request(message)

            print("Extracted:", result.model_dump())

            assert result is not None

    asyncio.run(run_test())
