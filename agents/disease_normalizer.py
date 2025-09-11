import requests
from time import sleep

class DiseaseNormalizer:
    """
    疾患名をOMIM/Orphanet標準IDに正規化するエージェント。
    TogoSeek API (collection: 'omim') を利用。
    """
    def __init__(self, top_k=1):
        self.api_url = "https://togoseek.dbcls.jp/search"
        self.headers = {"Content-Type": "application/json"}
        self.top_k = top_k

    def normalize(self, disease_name):
        """
        疾患名をOMIM/Orphanet標準IDに正規化する。
        Args:
            disease_name (str): 正規化したい疾患名
        Returns:
            dict: 正規化結果（OMIM/Orphanet ID, スコア等）
        """
        payload = {
            "query": disease_name,
            "collection": "omim",
            "metric": "euclid",
            "topK": self.top_k,
            "minCosineSimilarity": 0.3,
            "maxDistance": 1.3
        }
        try:
            response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            sleep(0.1)  # API負荷軽減
            if result and "results" in result and len(result["results"]) > 0:
                return result["results"][0]  # 最上位のみ返す
            else:
                return None
        except requests.exceptions.RequestException as e:
            print(f"[DiseaseNormalizer] APIリクエスト失敗: {e}")
            return None
