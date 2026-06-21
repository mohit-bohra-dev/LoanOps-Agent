import asyncio
import aioboto3
from botocore.config import Config

async def main():
    session = aioboto3.Session()
    import botocore
    c = Config(signature_version=botocore.UNSIGNED)
    async with session.client('bedrock-runtime', region_name='us-east-1', config=c) as client:
        try:
            await client.converse(modelId='test', messages=[{'role': 'user', 'content': [{'text': 'hi'}]}])
        except Exception as e:
            print(repr(e))

asyncio.run(main())
