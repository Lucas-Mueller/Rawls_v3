from utils.memory_summarizer import MemorySummarizer, SummaryContext

SAMPLE_MEMORY = (
    "In Phase 1 I ranked the floor principle first. "
    "By round three I shifted toward a floor constraint compromise after earnings fluctuated."
)

def test_summary_contains_key_details():
    summary = MemorySummarizer.create_summary(SAMPLE_MEMORY, SummaryContext.DISCUSSION, max_lines=2)
    assert "floor" in summary.lower()
    assert len(summary.splitlines()) <= 2

def test_insight_extraction_returns_sentences():
    insights = MemorySummarizer.extract_key_insights(SAMPLE_MEMORY)
    assert insights
    assert any("floor" in insight.lower() for insight in insights)
