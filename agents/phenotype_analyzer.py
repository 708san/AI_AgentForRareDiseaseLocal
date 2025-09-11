import requests
import os
from time import sleep
import re
from agents.disease_normalizer import DiseaseNormalizer

class PhenotypeAnalyzer:
    """
    HPOリストから診断候補を生成するエージェント。
    PubCaseFinder API（GET）とGemini API（LLMゼロショット）を併用。
    """
    def __init__(self, gemini_api_key=None):
        self.gemini_api_key = gemini_api_key or os.getenv("GOOGLE_API_KEY")

    def analyze_with_pubcasefinder(self, hpo_list):
        """
        PubCaseFinder APIで診断候補を取得し、必要な情報のみ抽出して返す。
        Args:
            hpo_list (list): HPOタームリスト
        Returns:
            list: 上位5件の {omim_disease_name_en, description, score} のみのリスト
        """
        hpo_ids = ",".join(hpo_list)
        url = f"https://pubcasefinder.dbcls.jp/api/pcf_get_ranked_list?target=omim&format=json&hpo_id={hpo_ids}"
        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            data = response.json()
            # 上位5件のみ、必要なフィールドだけ抽出
            top5 = []
            for item in data[:5]:
                top5.append({
                    "omim_disease_name_en": item.get("omim_disease_name_en", ""),
                    "description": item.get("description", ""),
                    "score": item.get("score", None)
                })
            return top5
        except Exception as e:
            print(f"[PhenotypeAnalyzer] PubCaseFinder API失敗: {e}")
            return []

    def analyze_with_gemini(self, hpo_list):
        """
        Gemini API (LLM) でゼロショット診断候補を取得。
        Args:
            hpo_list (list): HPOタームリスト
        Returns:
            list: 診断候補リスト
        """
        import google.generativeai as genai
        genai.configure(api_key=self.gemini_api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        prompt = self._build_prompt(hpo_list)
        try:
            response = model.generate_content(prompt)
            return response.text.split("\n")
        except Exception as e:
            print(f"[PhenotypeAnalyzer] Gemini API失敗: {e}")
            return []

    def _build_prompt(self, hpo_list):
        hpo_str = ", ".join(hpo_list)
        return f"You are a specialist in the field of rare diseases. Patient's HPO terms: {hpo_str}. List the top 5 most likely rare disease diagnoses.Be precise, and try to cover many unique possibilities.Each diagnosis should be a rare disease.Use ** to tag the disease name.Make sure to reorder the diagnoses from most likely to least likely.Now, List the top 5 diagnoses."
    def _build_prompt(self, hpo_list):
        hpo_str = ", ".join(hpo_list)
        return (
        f"You are a specialist in the field of rare diseases. "
        f"Patient's HPO terms: {hpo_str}. "
        "List the top 5 most likely rare disease diagnoses. "
        "Be precise, and try to cover many unique possibilities. "
        "Each diagnosis should be a rare disease. "
        "For each diagnosis, write the disease name enclosed in **(double asterisks) (e.g., **Disease Name**) at the beginning of the line. "
        "Make sure to reorder the diagnoses from most likely to least likely. "
        "Now, list the top 5 diagnoses."
        )
    
    def extract_disease_names_from_gemini(self, gemini_output):
        """
        Gemini出力（リスト）から疾患名のみ抽出しリストで返す
        Args:
            gemini_output (list): Geminiのテキスト出力リスト
        Returns:
            list: 疾患名リスト
        """
        disease_names = []
        for line in gemini_output:
            # 例: "1.  **Mitochondrial Disorders (e.g., Leigh Syndrome, MERRF, MELAS):** ..."
            match = re.search(r"\*\*(.+?)\*\*", line)
            if match:
                # 括弧やコロン以降を除去して病名部分だけ抽出
                name = match.group(1)
                # 例: "Mitochondrial Disorders (e.g., Leigh Syndrome, MERRF, MELAS):"
                name = re.split(r"[:（(]", name)[0].strip()
                disease_names.append(name)
        return disease_names

    def normalize_gemini_diseases(self,gemini_disease_names):
        normalizer = DiseaseNormalizer(top_k=1)
        normalized_list = []
        for name in gemini_disease_names:
            result = normalizer.normalize(name)
            if result and "id" in result and "label" in result:
                normalized_list.append({
                    "id": result["id"],
                    "label": result["label"]
                })
        return normalized_list


    def analyze(self, hpo_list):
        """
        PubCaseFinderとGemini両方の診断候補を統合して返す。
        Gemini出力は正規化用に疾患名リストも返す。
        """
        pubcase_candidates = self.analyze_with_pubcasefinder(hpo_list)
        gemini_candidates_raw = self.analyze_with_gemini(hpo_list)
        gemini_disease_names = self.extract_disease_names_from_gemini(gemini_candidates_raw)
        gemini_candidates = self.normalize_gemini_diseases(gemini_disease_names)
        return {
            "pubcasefinder": pubcase_candidates,
            "gemini": gemini_candidates
        }
