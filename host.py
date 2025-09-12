import os
from agents.knowledge_searcher import KnowledgeSearcher
from agents.case_searcher import CaseSearcher
from agents.phenotype_analyzer import PhenotypeAnalyzer
from agents.disease_normalizer import DiseaseNormalizer
from agents.self_reflection_agent import SelfReflectionAgent
import google.generativeai as genai

PROMPT4_TEMPLATE = """
You are a specialist in the field of rare diseases.
You have access to the following context:
- **Online knowledge** (with titles and URLs): {web_diagnosis}
- **LLM-generated diagnoses**: {llm_response}
- **Diagnosis API results**: {diagnosis_api_response}
- **Similar cases**: {similar_case_detailed}
- **Prompt details**: {patient_info}

Based on the above and your knowledge, enumerate the **top 5 most likely rare disease diagnoses** for this patient.

**For each diagnosis, use the following format:**

## **DIAGNOSIS NAME** (Rank #X/5)
### Diagnostic Reasoning:
- Provide 2-3 concise sentences explaining why this rare disease fits the clinical picture.
- Integrate evidence from all available sources (online knowledge, similar cases, LLM outputs, and API results).
- Support your reasoning with specific, in-text citations in [X] format, referencing the most relevant sources (including specific similar cases, articles, or diagnostic tools).
- Briefly discuss the pathophysiological basis for the diagnosis, citing relevant literature or case evidence.

**After listing all 5 diagnoses, include a reference section:**
## References:
- Number each reference in the order it is first cited ([1], [2], ...).
- Only include sources you directly cited in your diagnostic reasoning above.
- For each reference, should provide:
  a. Source type (e.g., medical guideline, similar case, literature, diagnosis assisent tool...)
  b. Use 3-4 sentences to describe of the content and its relevance.
  c. For articles or literature, include the title and URL if provided.
- Every in-text citation [X] in your reasoning should correspond to a numbered entry in your reference list.
- Try to cover as many sources and references.
- Do not repeat!!

**Key Instructions:**
1. Always use in-text citations in [X] format, matching only the references you actually cite in your reasoning.
2. Each diagnosis must be a rare disease (**bolded** using markdown).
3. Rank from most (#1) to least (#5) likely.
4. Integrate information from all provided sources (medical literature, similar cases, and judgment analyses) wherever appropriate.
5. Do **not** copy or invent references—only include those present in the provided materials.
6. Use bold formatting (**) only for the 'DIAGNOSIS NAME'. Do not use it anywhere else in the output.
"""





class RareDiseaseDiagnosisHost:
    """
    希少疾患診断支援AIエージェントの中央ホスト/制御クラス
    各エージェントを統合し、ワークフローを制御する
    """
    def __init__(self, config=None):
        self.config = config or {
            "knowledge_searcher": True,
            "case_searcher": False,
            "phenotype_analyzer": True,
            "disease_normalizer": True,
            "self_reflection": True
        }
        self.knowledge_searcher = KnowledgeSearcher()
        self.case_searcher = CaseSearcher()
        self.phenotype_analyzer = PhenotypeAnalyzer()
        self.disease_normalizer = DiseaseNormalizer()
        self.self_reflection_agent = SelfReflectionAgent(
            disease_normalizer=self.disease_normalizer,
            knowledge_searcher=self.knowledge_searcher,
             # 例: 2回まで自己反省
        )
        self.memory = []
        self.diagnosis_list = []


    
    def run(self, hpo_list):
        max_retry = 2  # In order to limit the usage of API Key, set maximum for self-reflection.
        retry_count = 0

        while (retry_count < max_retry):
        # collecting information and generating candidates
            if self.config["knowledge_searcher"]:
                knowledge = self.knowledge_searcher.search(", ".join(hpo_list))
            else:
                knowledge = []
            if self.config["case_searcher"]:
                cases = self.case_searcher.search(", ".join(hpo_list))
            else:
                cases = []
            if self.config["phenotype_analyzer"]:
                candidates = self.phenotype_analyzer.analyze(hpo_list)
            else:
                candidates = {"pubcasefinder": [], "gemini": []}
        # reset memory when it is first try.
            if retry_count == 0:
                self.memory = []
            self.memory.append({
                "knowledge": knowledge,
                "cases": cases,
                "candidates": candidates
            })

            prompt = PROMPT4_TEMPLATE.format(
            web_diagnosis=str(knowledge),
            llm_response=str(candidates.get("gemini")),
            diagnosis_api_response=str(candidates.get("pubcasefinder")),
            similar_case_detailed=str(cases),
            patient_info=str(hpo_list)
            )

            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            model = genai.GenerativeModel("gemini-2.5-flash")
            try:
                response = model.generate_content(prompt)
                diagnosis_report = response.text
            except Exception as e:
                print(f"[Host] Gemini診断レポート生成失敗: {e}")
                diagnosis_report = "診断レポート生成に失敗しました。"

        
            if self.config.get("self_reflection", True):
                reflection_result = self.self_reflection_agent.reflect(
                    diagnosis_report=diagnosis_report,
                    patient_info=", ".join(hpo_list),
                    similar_case_detailed=str(cases),
                )
                retry_count += 1
            else:
                reflection_result = None

        # acceptedがなければ再診断（上限回数まで）
            if reflection_result and reflection_result.get("accepted") == [] and retry_count < max_retry:
                retry_count += 1
                continue  # 1からやり直し
            else:
                break

        return {
        "diagnosis_report": diagnosis_report,
        "knowledge": knowledge,
        "cases": cases,
        "candidates": candidates,
        "self_reflection": reflection_result
        }

if __name__ == "__main__":
    # テスト用: HPOリストを与えて実行
    hpo_list = ["HP:0001250", "HP:0004322"]  # 例: てんかん, 筋力低下
    host = RareDiseaseDiagnosisHost()
    result = host.run(hpo_list)
    from pprint import pprint
    pprint(result)
