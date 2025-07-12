from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_openai import ChatOpenAI
from langchain.chains import GraphQAChain
from core.logger import LogManager


class AIKnowledgeGraph:
    def __init__(self, api_key: str, log_manager=None):
        self.api_key = api_key
        self.log_manager = log_manager or LogManager()
        self.llm = ChatOpenAI(
            temperature=0, model_name="gpt-4-turbo", openai_api_key=api_key)
        self.transformer = LLMGraphTransformer(llm=self.llm)
        self.graph = None
        self.qa_chain = None

    def build_graph(self, text: str) -> dict:
        """从文本自动抽取知识三元组并构建图谱"""
        try:
            self.graph = self.transformer.from_text(text)
            triples = self.graph.get_triples()
            # 可选：初始化问答链
            self.qa_chain = GraphQAChain.from_llm(
                self.llm, graph=self.graph, verbose=False)
            return {"triples": triples}
        except Exception as e:
            self.log_manager.error(f"知识图谱构建失败: {e}")
            return {"error": str(e)}

    def ask(self, question: str) -> dict:
        """对知识图谱进行自然语言问答"""
        try:
            if not self.qa_chain:
                return {"error": "请先构建知识图谱"}
            answer = self.qa_chain.run(question)
            return {"answer": answer}
        except Exception as e:
            self.log_manager.error(f"知识图谱问答失败: {e}")
            return {"error": str(e)}

    def get_triples(self) -> dict:
        try:
            if not self.graph:
                return {"error": "请先构建知识图谱"}
            return {"triples": self.graph.get_triples()}
        except Exception as e:
            self.log_manager.error(f"获取知识三元组失败: {e}")
            return {"error": str(e)}
