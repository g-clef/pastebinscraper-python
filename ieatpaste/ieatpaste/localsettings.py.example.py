DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": "",
        "USER": "",
        "PASSWORD": "",
        "HOST": "127.0.0.1",
        "PORT": "5432",
    }
}

ElasticsearchURL = "<insert host + port for elasticsearch here>"
ElasticsearchIndex = "paste"
ElasticsearchPercolateIndex = "pastepercolates"
