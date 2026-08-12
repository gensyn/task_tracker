class Blueprint:
    def __init__(self, data, expected_domain, path, schema):
        self.data = data
        self.expected_domain = expected_domain
        self.path = path
        self.schema = schema
