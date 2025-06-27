class BaseModel:
    def __init__(self, **data):
        for k, v in data.items():
            setattr(self, k, v)

    @classmethod
    def model_validate(cls, obj, *, strict=None, from_attributes=None, context=None):
        return cls(**obj)

ConfigDict = dict

def field(default=None, default_factory=None):
    if default_factory is not None:
        return default_factory()
    return default

# provide expected name
Field = field
