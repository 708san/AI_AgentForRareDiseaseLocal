import re
import os
import google.generativeai as genai

PROMPT6_TEMPLATE = """
Assume you are a doctor specialized in rare disease diagnosis.
Based on the patient information, similar case diagnoses, and disease knowledge, evaluate whether the proposed diagnosis is correct for this patient.
Begin with a clear 'DIAGNOSIS ASSESSMENT: [Correct/Incorrect]' statement, followed by your reasoning.
Structure your analysis as follows:
1. PATIENT SUMMARY: Briefly summarize the patient's key symptoms
2. PROPOSED DIAGNOSIS ANALYSIS: Evaluate the proposed diagnosis ({diagnosis_to_judge}) in relation to the patient's symptoms
3. REFERENCES: Extract and number the most relevant evidence from the provided medical literature that supports your conclusion
Patient phenotype: {patient_info}
Similar cases: {similar_case_detailed}
Medical literature: {disease_knowledge}
"""

class SelfReflectionAgent:
    """
    診断レポートから各疾患の妥当性を自己評価し、必要に応じて再診断を行うエージェント。
    """
    def __init__(self, disease_normalizer, knowledge_searcher, max_reflection=1, gemini_api_key=None):
        self.disease_normalizer = disease_normalizer
        self.knowledge_searcher = knowledge_searcher
        self.max_reflection = max_reflection
        self.gemini_api_key = gemini_api_key or os.getenv("GOOGLE_API_KEY")
        genai.configure(api_key=self.gemini_api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")

    def extract_disease_names(self, diagnosis_report):
        """
        診断レポートから**で囲まれた病名を抽出
        """
        return re.findall(r"\*\*(.+?)\*\*", diagnosis_report)

    def normalize_diseases(self, disease_names):
        """
        DiseaseNormalizerで病名を正規化し、id/labelリストを返す
        """
        normalized = []
        for name in disease_names:
            result = self.disease_normalizer.normalize(name)
            if result and "id" in result and "label" in result:
                normalized.append({"id": result["id"], "label": result["label"]})
        return normalized

    def search_knowledge(self, disease_list):
        
        results = []
        for d in disease_list:
            res = self.knowledge_searcher.search(d["label"])
            results.append({"disease": d, "knowledge": res})
        return results

    def evaluate_diagnosis(self, patient_info, similar_case_detailed, disease_knowledge, diagnosis_to_judge):
        """
        Prompt6を使って診断評価をGeminiで実行
        """
        prompt = PROMPT6_TEMPLATE.format(
            patient_info=patient_info,
            similar_case_detailed=similar_case_detailed,
            disease_knowledge=disease_knowledge,
            diagnosis_to_judge=diagnosis_to_judge
        )
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"[SelfReflectionAgent] Gemini診断評価失敗: {e}")
            return "診断評価生成に失敗しました。"

    def reflect(self, diagnosis_report, patient_info, similar_case_detailed, info_amount=1, re_diagnose_callback=None):
        """
        自己反省ループ本体。Prompt4の診断レポートを各疾患ごとに分割し、
        各病名に対して正規化・知識検索・Prompt6による精査を行う。
        全て棄却された場合のみ再診断。
        受理された診断のみ返す。
        """
        for i in range(self.max_reflection):
            diagnosis_blocks = re.split(r'## \*\*(.+?)\*\* \(Rank #[0-9]+/5\)', diagnosis_report)
            disease_blocks = []
            for idx in range(1, len(diagnosis_blocks), 2):
                disease_name = diagnosis_blocks[idx].strip()
                block_text = diagnosis_blocks[idx+1] if idx+1 < len(diagnosis_blocks) else ''
                disease_blocks.append((disease_name, block_text))
            accepted = []
            for disease_name, block_text in disease_blocks:
                norm = self.disease_normalizer.normalize(disease_name)
                if not (norm and 'id' in norm and 'label' in norm):
                    continue
                know = self.knowledge_searcher.search(norm["label"])
                eval_result = self.evaluate_diagnosis(
                    patient_info=patient_info,
                    similar_case_detailed=similar_case_detailed,
                    disease_knowledge=str(know),
                    diagnosis_to_judge=disease_name+block_text
                )
                if "DIAGNOSIS ASSESSMENT: [Correct]" in eval_result:
                    accepted.append({
                        "disease": norm,
                        "eval": eval_result,
                        "block_text": block_text
                    })
            if accepted:
                return {"accepted": accepted, "reflection_count": i+1}
        return {"accepted": [], "reflection_count": self.max_reflection}
