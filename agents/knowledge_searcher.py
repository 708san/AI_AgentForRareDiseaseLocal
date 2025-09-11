from langchain.utilities import WikipediaAPIWrapper

class KnowledgeSearcher:
    """
    Wikipedia検索を使った知識検索エージェント
    """
    def __init__(self, lang="ja"):
        self.wiki = WikipediaAPIWrapper(lang=lang)

    def search(self, query):
        """
        Wikipediaから検索し、要約を返す
        Args:
            query (str): 検索クエリ
        Returns:
            list: 検索結果リスト（タイトル・要約・URL）
        """
        result = self.wiki.run(query)
        url = f"https://{self.wiki.lang}.wikipedia.org/wiki/{query.replace(' ', '_')}"
        return [{
            "title": query,
            "summary": result,
        }]
