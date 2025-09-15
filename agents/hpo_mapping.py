import json
import os

class HPOMapping:
    """
    HPO IDリストを"HPid:label"形式のリストに変換するユーティリティクラス
    """
    def __init__(self, mapping_path=None):
        if mapping_path is None:
            mapping_path = os.path.join(os.path.dirname(__file__), '../data/HPO_matching/phenotype_mapping.json')
        with open(mapping_path, encoding='utf-8') as f:
            self.mapping = json.load(f)

    def convert(self, hpoid_list):
        result = []
        for hpoid in hpoid_list:
            label = self.mapping.get(hpoid, "Unknown")
            result.append(f"{hpoid}:{label}")
        return result
