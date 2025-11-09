from utils.memory_summarizer import MemorySummarizer, SummaryContext

SAMPLE_MEMORY = (
    "In Phase 1 I ranked the floor principle first. "
    "By round three I shifted toward a floor constraint compromise after earnings fluctuated."
)


def test_summary_contains_key_details(text_regression):
    summary = MemorySummarizer.create_summary(SAMPLE_MEMORY, SummaryContext.DISCUSSION, max_lines=2)
    assert len(summary.splitlines()) <= 2
    text_regression.check(summary)


def test_insight_extraction_returns_sentences(data_regression):
    insights = MemorySummarizer.extract_key_insights(SAMPLE_MEMORY)
    assert insights
    data_regression.check({"insights": insights})
