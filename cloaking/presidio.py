from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine


analyzer = AnalyzerEngine()

anonymizer = AnonymizerEngine()



def anonymize_text(text, language="en"):
    results = analyzer.analyze(text=text, language=language)
    anonymized_text = anonymizer.anonymize(
    text=text,
    analyzer_results=results
    )
    return anonymized_text.text
