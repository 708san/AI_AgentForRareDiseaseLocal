import os
import numpy as np
import pickle
import google.generativeai as genai

class DiseaseNormalizer:
    def __init__(self, embeddings_path= "./data/omim_embeddings.pkl"):
        """
        コンストラクタ。事前計算されたembeddingデータをロードし、APIキーを設定する。
        """
        # 環境変数からGoogle APIキーを読み込む
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("環境変数 'GOOGLE_API_KEY' が設定されていません。")
        
        genai.configure(api_key=api_key)

        with open(embeddings_path, 'rb') as f:
            normalized_data = pickle.load(f)
            self.omim_vectors = normalized_data['vectors']
            self.omim_ids = normalized_data['ids']
            self.omim_labels = normalized_data['labels']
        
        # ベクトルを正規化（L2ノルムで割る）
        self.omim_vectors /= np.linalg.norm(self.omim_vectors, axis=1, keepdims=True)
        
        print("DiseaseNormalizerの準備ができました。")

    def normalize(self, disease_name):
        """
        疾患名を受け取り、最も類似したOMIM疾患のIDと病名を返す。
        """
        # 入力された疾患名をembedding
        result = genai.embed_content(
            model="models/embedding-001",
            content=disease_name,
            task_type="RETRIEVAL_QUERY"
        )
        query_vector = np.array(result['embedding'])

        # ベクトルを正規化
        query_vector /= np.linalg.norm(query_vector)

        # コサイン類似度を計算 (内積)
        similarities = np.dot(self.omim_vectors, query_vector.T).flatten()

        # 最も類似度が高い疾患のインデックスを取得
        closest_index = np.argmax(similarities)

        return {
            'id': self.omim_ids[closest_index],
            'name': self.omim_labels[closest_index],
            'similarity': similarities[closest_index]
        }

"""
try:
    normalizer = DiseaseNormalizer()
    result = normalizer.normalize("LIPPEL-FEIL SYNDROME 2, AUTOSOMAL RECESSIVE; KFS")
    print(f"入力: LIPPEL-FEIL SYNDROME 2, AUTOSOMAL RECESSIVE; KFS")
    print(f"正規化結果: {result}")
    
    result_2 = normalizer.normalize("INFLAMMATORY BOWEL DISEASE 25, AUTOSOMAL RECESSIVE; IBD")
    print(f"入力: INFLAMMATORY BOWEL DISEASE 25, AUTOSOMAL RECESSIVE; IBD")
    print(f"正規化結果: {result_2}")
#
except (ValueError, FileNotFoundError) as e:
    print(e)
    print("エラー: 'omim_embeddings.pkl' が見つかりません。先に事前準備のコードを実行してください。")
"""