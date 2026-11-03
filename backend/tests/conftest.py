import pytest

from papersensei.config import ROOT, Settings
from papersensei.llm import PaperContext, ScriptedLLM
from papersensei.pdf import parse_pdf
from papersensei.service import Service
from papersensei.store import Store

SAMPLE = ROOT / "samples" / "hybrid-retrieval.pdf"


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(llm="scripted", data_dir=tmp_path)


@pytest.fixture
def paper() -> PaperContext:
    data = SAMPLE.read_bytes()
    return PaperContext(data, parse_pdf(data))


@pytest.fixture
def service(settings) -> Service:
    return Service(settings, ScriptedLLM(), Store(settings.data_dir))
