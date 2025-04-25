from natasha import (
    Segmenter, MorphVocab, NewsEmbedding,
    NewsMorphTagger, Doc
)

class NLPProcessor:
    def __init__(self):
        self.segmenter = Segmenter()
        self.morph_vocab = MorphVocab()
        emb = NewsEmbedding()
        self.morph_tagger = NewsMorphTagger(emb)

    def process(self, text):
        doc = Doc(text)
        doc.segment(self.segmenter)
        doc.tag_morph(self.morph_tagger)
        return doc