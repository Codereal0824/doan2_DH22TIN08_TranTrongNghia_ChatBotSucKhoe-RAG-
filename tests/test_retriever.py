from backend.rag.retriever import RAGRetriever


class MockVectorStore:
    def search(self, embedding, top_k=5):
        # Trả về các documents mock với score (điểm càng thấp càng liên quan)
        return [
            {"content": "Cảm cúm là bệnh thường gặp.", "metadata": {
                "source": "cam_cum.txt"}, "score": 80.0, "similarity": 0.8},
            {"content": "Béo phì do lối sống nguyên nhân chính không do di truyền.",
                "metadata": {"source": "beo_phi.txt"}, "score": 90.0, "similarity": 0.5},
            {"content": "Cách làm bánh kem tại nhà.", "metadata": {
                "source": "irrelevant.txt"}, "score": 180.0, "similarity": 0.1}
        ]


class MockEmbeddingModel:
    @property
    def embedding_dim(self):
        return 768

    def encode_text(self, text):
        return [0.1] * 768


def test_retrieve_returns_documents():
    """Test khả năng trả về documents từ Mock Vector Store cùa retriever"""
    mock_vs = MockVectorStore()
    mock_embed = MockEmbeddingModel()

    retriever = RAGRetriever(vector_store=mock_vs,
                             embedder=mock_embed, top_k=3)

    # 1. Bật lọc: Áp dụng RELEVANCE_THRESHOLD (mặc định >140 bị reject)
    docs_filtered = retriever.retrieve(
        "Thông tin sức khỏe", apply_threshold=True)
    assert len(docs_filtered) == 2
    assert docs_filtered[0]["metadata"]["source"] == "cam_cum.txt"

    # 2. Không lọc (Trả về all top_k doc được vector_store search gửi ra)
    docs_unfiltered = retriever.retrieve("Tất cả", apply_threshold=False)
    assert len(docs_unfiltered) == 3


def test_extract_disease_keywords():
    """Test khả năng phát hiện từ khóa để apply boosting cho kết quả"""
    retriever = RAGRetriever(
        vector_store=MockVectorStore(), embedder=MockEmbeddingModel())

    keywords = retriever._extract_disease_keywords(
        "Cách phòng chống bệnh béo phì ở trẻ em")
    assert "béo phì" in keywords
    assert "ung thư" not in keywords
