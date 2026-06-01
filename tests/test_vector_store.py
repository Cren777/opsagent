import importlib
import sys
import types


class FakeMilvusClient:
    instances = []

    def __init__(self, db_path):
        self.db_path = db_path
        self.loaded = set()
        self.load_calls = []
        self.query_before_load_count = 0
        FakeMilvusClient.instances.append(self)

    def has_collection(self, collection_name):
        return True

    def load_collection(self, collection_name):
        self.loaded.add(collection_name)
        self.load_calls.append(collection_name)

    def query(self, collection_name, **kwargs):
        if collection_name not in self.loaded:
            self.query_before_load_count += 1
            raise RuntimeError("collection released")
        return [{"id": 1}]

    def search(self, collection_name, **kwargs):
        if collection_name not in self.loaded:
            raise RuntimeError("collection released")
        return [[{
            "entity": {
                "content": "matched log",
                "source_file": "ops_agent.log",
                "title": "runtime log",
                "chunk_index": 0,
            },
            "distance": 0.91,
        }]]


def import_vector_store(monkeypatch, tmp_path):
    FakeMilvusClient.instances = []
    settings = types.SimpleNamespace(
        milvus_knowledge_collection="ops_knowledge",
        embedding_dim=4,
        milvus_db_path=str(tmp_path / "milvus.db"),
    )
    monkeypatch.setitem(sys.modules, "config.settings", types.SimpleNamespace(settings=settings))
    monkeypatch.setitem(
        sys.modules,
        "pymilvus",
        types.SimpleNamespace(
            MilvusClient=FakeMilvusClient,
            DataType=types.SimpleNamespace(INT64="INT64", FLOAT_VECTOR="FLOAT_VECTOR", VARCHAR="VARCHAR", INT32="INT32"),
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "loguru",
        types.SimpleNamespace(logger=types.SimpleNamespace(info=lambda *args, **kwargs: None)),
    )
    sys.modules.pop("ops_agent.data.vector_store", None)
    return importlib.import_module("ops_agent.data.vector_store")


def test_existing_collection_is_loaded_on_init(monkeypatch, tmp_path):
    module = import_vector_store(monkeypatch, tmp_path)

    store = module.VectorStore("ops_logs")

    assert store.client.load_calls == ["ops_logs"]


def test_search_loads_collection_before_has_data_probe(monkeypatch, tmp_path):
    module = import_vector_store(monkeypatch, tmp_path)
    store = module.VectorStore("ops_logs")
    store.client.loaded.clear()

    result = store.search([0.1, 0.2, 0.3, 0.4], top_k=1)

    assert result[0]["content"] == "matched log"
    assert store.client.query_before_load_count == 0
