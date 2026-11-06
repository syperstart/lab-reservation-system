# =====================================================================
# RAG 知识库服务（kb_service）
# =====================================================================
# 一句话理解本模块：
#   把 knowledge/ 里的 Markdown 问答库读进来 → 转成向量 → 存进 ChromaDB，
#   用户提问时查出最相关的几条知识，交给大模型照着回答。
#
# 整个流程只有 4 步（每步一个函数，按顺序看即可）：
#   第 1 步 load_documents()  读文件：knowledge/*.md → 知识块列表
#   第 2 步 _embed()          转向量：文本 → 一串数字（本地哈希，无需下载模型）
#   第 3 步 build_index()     存起来：向量写入 ChromaDB（服务启动时执行一次）
#   第 4 步 search()          查出来：用户问题 → 最相关的知识块文本
#
# 两个「为什么这样设计」：
#   ▸ 为什么 ChromaDB 用内存模式？知识库只有几十条，每次启动重建索引毫秒级完成；
#     且 chromadb 1.5 的落盘引擎在本项目「含中文的路径」下会报错，内存模式直接绕开。
#   ▸ 为什么向量用字符 n-gram 哈希而不是大模型？中文短问答靠「用词重叠」就能匹配得很好，
#     哈希向量纯本地计算、离线可用；想换语义模型时，只需替换 _embed 函数（注释里有写法）。
# =====================================================================

import hashlib
import re
import zlib
from pathlib import Path

import chromadb
import numpy as np

# 配置：知识库目录 / 集合名 / 检索条数
from app.config import settings

# 业务异常：本项目统一用 BusinessException 报告业务错误
from common.exceptions import BusinessException

# 向量维度：把文本哈希到 2048 个「数字桶」里，几十条知识完全够用
EMBED_DIM = 2048

# ChromaDB 集合：全局只创建一次（第一次使用时创建，之后复用）
_collection = None


# ---------------- 第 2 步：文本 → 向量 ----------------

def _hash_gram(gram: str) -> int:
    """把「一个字」或「两个字」稳定地哈希成一个 0~2047 的桶编号。

    用 crc32 而不是 Python 内置 hash()：内置 hash 每次启动随机加盐，
    会导致两次运行向量对不上（索引和查询必须用同一套哈希）。
    """
    return zlib.crc32(gram.encode("utf-8")) % EMBED_DIM


def _embed(text: str) -> list[float]:
    """把文本转成向量：统计每个「字 / 双字」落在哪个桶，组成 2048 维数字。

    例：「怎么预约」→ 单字 怎/么/预/约（各记 1 分）+ 双字 怎么/么预/预约（各记 2 分）。
    用词越像的两段文本，向量越接近，后面用余弦相似度就能排出「谁最相关」。
    最后做一次 L2 归一化，让比较只跟「用词分布」有关、不受文本长短影响。

    想换成真正的语义模型（效果更好但需联网下载模型），只需替换本函数为：
        from chromadb.utils import embedding_functions
        _ef = embedding_functions.ONNXMiniLM_L6_V2()
        return _ef([text])[0]
    """
    vec = np.zeros(EMBED_DIM)
    text = text.lower()
    for i in range(len(text)):
        # 单字窗口：跳过空格，避免无意义的空格占桶
        ch = text[i]
        if not ch.isspace():
            vec[_hash_gram(ch)] += 1.0
        # 双字窗口：双字更能代表中文词义，权重给 2 分
        if i + 1 < len(text):
            pair = text[i : i + 2]
            if not pair.isspace():
                vec[_hash_gram(pair)] += 2.0
    # L2 归一化：把向量长度缩放到 1
    norm = float(np.linalg.norm(vec))
    if norm > 0:
        vec = vec / norm
    return vec.tolist()


# ---------------- 第 1 步：读文件、解析知识库 ----------------

def _after_colon(line: str) -> str:
    """取一行冒号后面的内容，例如「- 问法：怎么登录 / 登录入口」→「怎么登录 / 登录入口」。"""
    for sep in ("：", ":"):
        if sep in line:
            return line.split(sep, 1)[1].strip()
    return line.strip()


def _parse_qa_block(block: str) -> dict | None:
    """解析一个「## Q1：问题」段落 → {question, text}。没有答案的段落返回 None。"""
    question = ""
    variants = ""
    answer = ""
    for raw in block.splitlines():
        line = raw.strip()
        if line.startswith("## "):
            # 「## Q1：怎么登录系统？」→ 去掉「## Q1：」前缀，只留问题
            question = re.sub(r"^##\s*Q?\d*\s*[：:]\s*", "", line).strip()
        elif line.startswith("- 问法"):
            variants = _after_colon(line)
        elif line.startswith("- 答案"):
            answer = _after_colon(line)

    # 标题、说明等没有「答案」的段落直接跳过
    if not answer:
        return None

    # text = 将来给大模型看的原文（也是向量化的对象）
    head = f"问题：{question}\n" if question else ""
    return {
        "question": question or variants or "未命名问题",
        "text": f"{head}问法：{variants}\n答案：{answer}",
    }


def _parse_table_row(line: str) -> dict | None:
    """解析「| 提示 | 原因 | 处理办法 |」表格的一行 → 知识块。表头/分隔行返回 None。"""
    line = line.strip()
    if not line.startswith("|"):
        return None
    # 去掉首尾竖线再按竖线切分，得到 3 列
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if len(cells) < 3 or "---" in line:  # 分隔行 |---|---| 跳过
        return None
    phenomenon, reason, solution = cells[0], cells[1], cells[2]
    if reason == "原因" and solution == "处理办法":  # 表头行跳过
        return None
    if not phenomenon or not solution:
        return None
    return {
        "question": phenomenon,
        "text": f"提示：{phenomenon}\n原因：{reason}\n处理办法：{solution}",
    }


def load_documents() -> list[dict]:
    """第 1 步：把 knowledge/ 下所有 .md 文件解析成知识块列表。

    支持两种格式（自动识别，互不干扰）：
      1) Q&A 问答（01~05 号文件）：
           ## Q1：怎么登录系统？
           - 问法：怎么登录 / 登录入口在哪
           - 答案：打开登录页，输入账号密码……
      2) 报错对照表（06 号文件）：
           | 账号或密码错误 | 账号不存在 | 确认账号… |
    00 号是目录索引（导航用），不含问答，跳过。

    返回 list[dict]，每项 = {source 文件名, question 问题, text 全文}
    """
    kb_dir = Path(settings.KB_DIR)
    if not kb_dir.is_dir():
        raise BusinessException(f"知识库目录不存在：{kb_dir}")

    docs: list[dict] = []
    for md_file in sorted(kb_dir.glob("*.md")):
        if md_file.name.startswith("00-"):  # 跳过索引文件
            continue
        content = md_file.read_text(encoding="utf-8")

        # 方式 A：按「## 」标题切块，逐块解析 Q&A
        for block in re.split(r"\n(?=##\s)", content):
            doc = _parse_qa_block(block)
            if doc:
                doc["source"] = md_file.name
                docs.append(doc)
        # 方式 B：逐行解析表格（Q&A 文件里没有 | 行，不会重复）
        for line in content.splitlines():
            doc = _parse_table_row(line)
            if doc:
                doc["source"] = md_file.name
                docs.append(doc)
    return docs


# ---------------- 第 3 步：写进 ChromaDB ----------------

def _get_collection():
    """获取 ChromaDB 集合：第一次调用时创建，之后复用同一个（全局单例）。

    内存模式（EphemeralClient）：数据只活在本进程里，服务重启即清空；
    好在知识库很小，重启后 build_index 重建只要毫秒级，不需要落盘。
    """
    global _collection
    if _collection is None:
        client = chromadb.EphemeralClient()
        _collection = client.get_or_create_collection(
            name=settings.KB_COLLECTION,
            metadata={"hnsw:space": "cosine"},  # 用余弦相似度比较向量
        )
    return _collection


def _doc_id(source: str, question: str) -> str:
    """生成一条知识的固定 id：同文件同问题 → 永远同一个 id（幂等写入的关键）。"""
    return hashlib.md5(f"{source}::{question}".encode("utf-8")).hexdigest()


def build_index() -> int:
    """第 3 步：把全部知识块「向量化 + 写入」ChromaDB，返回条数。

    幂等：同一条知识 id 固定，重复执行只会覆盖不会写重复（启动时放心调用）。
    """
    docs = load_documents()
    if not docs:
        raise BusinessException("知识库为空，没有可加载的内容")

    collection = _get_collection()
    collection.upsert(
        ids=[_doc_id(d["source"], d["question"]) for d in docs],  # 每条知识的编号
        documents=[d["text"] for d in docs],                      # 原文（检索结果直接用它）
        embeddings=[_embed(d["text"]) for d in docs],             # 向量（第 2 步算出来）
        metadatas=[{"source": d["source"]} for d in docs],        # 出处文件名
    )
    return len(docs)


# ---------------- 第 4 步：按问题检索 ----------------

def search(query: str, top_k: int = 3) -> list[str]:
    """第 4 步：把用户问题向量化，返回最相似的 top_k 条知识全文（按相关度从高到低）。

    首次使用且集合还是空的（比如没走 main.py 启动流程）→ 自动先建索引。
    """
    if not query or not query.strip():
        return []

    collection = _get_collection()
    if collection.count() == 0:  # 还没建索引 → 先建
        build_index()

    result = collection.query(
        query_embeddings=[_embed(query.strip())],  # 问题也要用同一套向量化
        n_results=min(top_k, collection.count()),  # 最多取 top_k 条
    )
    # query 返回形如 {"documents": [["文1", "文2"]]}：外层是「每个查询一组」，这里取第 0 组
    docs = result.get("documents")
    return docs[0] if docs else []


def build_context(query: str, top_k: int = 3) -> str:
    """把检索结果拼成一段可直接放进大模型 messages 的上下文文本。

    任何失败（知识库出问题等）都返回空串：RAG 只是增强，绝不能拖垮对话主流程。
    """
    try:
        hits = search(query, top_k)
    except Exception:
        return ""  # 静默降级：没有知识库也照样用系统提示词回答
    if not hits:
        return ""

    lines = ["以下是知识库中与用户问题最相关的问答内容，请优先依据它们回答，不要编造："]
    for i, text in enumerate(hits, 1):
        lines.append(f"【{i}】{text}")
    return "\n".join(lines)
