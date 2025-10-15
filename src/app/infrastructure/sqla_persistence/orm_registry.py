from sqlalchemy import MetaData
from sqlalchemy.orm import registry

metadata = MetaData()
mapping_registry = registry(metadata=metadata)
