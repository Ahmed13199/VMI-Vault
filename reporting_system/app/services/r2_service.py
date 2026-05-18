import os
from datetime import timedelta

import boto3
from botocore.config import Config


class R2Service:
    @staticmethod
    def _env(*names: str):
        for name in names:
            value = os.environ.get(name)
            if value:
                return value
        return None

    @staticmethod
    def _client():
        account_id = R2Service._env('R2_ACCOUNT_ID')
        endpoint_url = R2Service._env('R2_ENDPOINT_URL', 'R2_ENDPOINT')
        if not endpoint_url and account_id:
            endpoint_url = f'https://{account_id}.r2.cloudflarestorage.com'

        access_key_id = R2Service._env('R2_ACCESS_KEY_ID')
        secret_access_key = R2Service._env('R2_SECRET_ACCESS_KEY')
        region_name = R2Service._env('R2_REGION') or 'auto'

        if not endpoint_url or not access_key_id or not secret_access_key:
            raise RuntimeError(
                'R2 credentials are not configured. Set R2_ACCESS_KEY_ID, '
                'R2_SECRET_ACCESS_KEY, and either R2_ENDPOINT/R2_ENDPOINT_URL '
                'or R2_ACCOUNT_ID.'
            )

        return boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region_name,
            config=Config(signature_version='s3v4')
        )

    @staticmethod
    def upload_fileobj(fileobj, key: str, content_type: str | None = None):
        bucket = R2Service._env('R2_BUCKET_NAME')
        if not bucket:
            raise RuntimeError('R2 bucket is not configured. Set R2_BUCKET_NAME.')

        extra = {}
        if content_type:
            extra['ContentType'] = content_type

        client = R2Service._client()
        client.upload_fileobj(fileobj, bucket, key, ExtraArgs=extra or None)

    @staticmethod
    def delete_object(key: str):
        bucket = R2Service._env('R2_BUCKET_NAME')
        if not bucket:
            raise RuntimeError('R2 bucket is not configured. Set R2_BUCKET_NAME.')

        client = R2Service._client()
        client.delete_object(Bucket=bucket, Key=key)

    @staticmethod
    def presigned_get_url(key: str, expires_in_seconds: int = 600) -> str:
        bucket = R2Service._env('R2_BUCKET_NAME')
        if not bucket:
            raise RuntimeError('R2 bucket is not configured. Set R2_BUCKET_NAME.')

        client = R2Service._client()
        return client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=expires_in_seconds
        )

    @staticmethod
    def public_url(key: str) -> str | None:
        base = R2Service._env('R2_PUBLIC_URL_BASE')
        if not base:
            return None
        return f"{base.rstrip('/')}/{key.lstrip('/')}"
