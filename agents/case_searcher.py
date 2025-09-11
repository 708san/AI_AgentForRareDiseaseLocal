import requests
from time import sleep

class CaseSearcher:
    """
    類似症例をTogoSeek API (collection: 'case') で検索するエージェント。
    """
    def __init__(self, top_k=5):
        self.api_url = "https://togoseek.dbcls.jp/search"
        self.headers = {"Content-Type": "application/json"}
        self.top_k = top_k

    def search(self, hpo_query):
        """
        HPOリストをクエリとして症例DBから類似症例を検索。
        Args:
            hpo_query (str): カンマ区切りHPOターム
        Returns:
            list: 類似症例リスト
        """
        payload = {
            "query": hpo_query,
            "collection": "case",
            "metric": "euclid",
            "topK": self.top_k,
            "minCosineSimilarity": 0.3,
            "maxDistance": 1.3
        }
        try:
            response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            sleep(0.1)
            return result.get("results", [])
        except requests.exceptions.RequestException as e:
            print(f"[CaseSearcher] APIリクエスト失敗: {e}")
            return []
