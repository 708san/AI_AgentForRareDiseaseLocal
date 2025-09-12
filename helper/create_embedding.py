import os
import json
import pickle
import time # timeモジュールをインポート
import numpy as np
import google.generativeai as genai
from tqdm import tqdm # 進捗表示のためにtqdmをインポート

def create_omim_embeddings(omim_mapping_path, output_path, batch_size=100):
    """
    omim_mapping.jsonを読み込み、レートリミットを考慮しながら
    バッチ処理で各疾患名をembeddingして保存する関数。
    """
    # 環境変数からGoogle APIキーを読み込む
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("環境変数 'GOOGLE_API_KEY' が設定されていません。")
    
    genai.configure(api_key=api_key)

    with open(omim_mapping_path, 'r', encoding='utf-8') as f:
        omim_data = json.load(f)

    omim_ids = list(omim_data.keys())
    omim_labels = list(omim_data.values())

    print(f"{len(omim_labels)}件のOMIM疾患名をembeddingします (バッチサイズ: {batch_size})")

    all_embeddings = []
    
    # バッチ処理のループ (tqdmで進捗を表示)
    for i in tqdm(range(0, len(omim_labels), batch_size), desc="Embedding Progress"):
        batch_labels = omim_labels[i:i + batch_size]
        
        try:
            # Googleのembeddingモデルを利用
            result = genai.embed_content(
                model="models/embedding-001",
                content=batch_labels,
                task_type="RETRIEVAL_DOCUMENT"
            )
            all_embeddings.extend(result['embedding'])
        
        except Exception as e:
            print(f"バッチ {i//batch_size + 1} の処理中にエラーが発生しました: {e}")
            # エラーが発生した場合、少し長めに待機してリトライするなどの処理も考えられます
            time.sleep(10) # 10秒待機
            continue

        # APIのレートリミットを避けるために1秒待機
        time.sleep(1)

    omim_vectors = np.array(all_embeddings)
    
    # embeddingが成功したデータのみを保存対象とする
    successful_count = len(omim_vectors)
    
    normalized_data = {
        'vectors': omim_vectors,
        'ids': omim_ids[:successful_count],
        'labels': omim_labels[:successful_count]
    }

    with open(output_path, 'wb') as f:
        pickle.dump(normalized_data, f)

    print(f"\n{successful_count}件のEmbeddingデータを {output_path} に保存しました。")



try:
    create_omim_embeddings('./data/omim_mapping.json', './data/omim_embeddings.pkl')
except ValueError as e:
    print(e)