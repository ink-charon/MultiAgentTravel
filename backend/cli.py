#!/usr/bin/env python3
"""智能旅行规划助手 — 终端版本"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich import box

console = Console()

BANNER = """
[bold cyan]╔══════════════════════════════════════════════╗
║   ✈️  智能旅行规划助手  -  终端版本  ✈️      ║
║  LangChain Agent · 知识库检索 · 多轮对话 · Debug ║
╚══════════════════════════════════════════════╝[/bold cyan]
"""

EXIT_WORDS = {"quit", "exit", "q", "退出"}


def init_cli_agent():
    """初始化所有服务"""
    from config import config
    config.ensure_dirs()

    from prompts import PromptLoader
    from tools import WeatherTool, TicketTool, SearchTool, MapTool, DrawingTool

    prompt_loader = PromptLoader(config.PROMPTS_DIR)
    tools = [
        WeatherTool(api_key=config.WEATHER_API_KEY, api_host=config.WEATHER_API_HOST),
        TicketTool(use_mock=config.USE_MOCK_TICKET),
        SearchTool(api_key=config.TAVILY_API_KEY),
        MapTool(api_key=config.AMAP_API_KEY),
        DrawingTool(output_dir=config.IMAGES_DIR),
    ]

    from agent import MultiTravelAgent
    from knowledge import VectorStore, MemoryManager, ForgettingManager
    from document import TextSplitter, DocumentPipeline, Embedder

    # 中文嵌入模型（魔搭社区 bge-large-zh-v1.5）
    try:
        embedder = Embedder(model_name=config.EMBEDDING_MODEL, cache_dir=config.MODELS_DIR)
        _ = embedder.embed_query("test")  # 触发加载
        console.print("[dim]中文嵌入模型已加载: bge-large-zh-v1.5[/dim]")
    except Exception as e:
        console.print(f"[yellow]⚠️ 嵌入模型加载失败，使用 ChromaDB 默认: {e}[/yellow]")
        embedder = None

    vector_store = VectorStore(persist_dir=config.CHROMA_DIR, embedding_function=embedder)
    memory_manager = MemoryManager(vector_store)
    forgetting_manager = ForgettingManager(vector_store)
    splitter = TextSplitter(chunk_size=config.CHUNK_SIZE, chunk_overlap=config.CHUNK_OVERLAP)
    doc_pipeline = DocumentPipeline(splitter=splitter, embedder=embedder, vector_store=vector_store)

    agent = MultiTravelAgent(
        tools=tools, prompt_loader=prompt_loader, debug=True,
        vector_store=vector_store, doc_pipeline=doc_pipeline, memory_manager=memory_manager,
    )
    return agent, vector_store, forgetting_manager


async def show_menu() -> str:
    """显示主菜单"""
    console.print()
    menu = Table(box=box.ROUNDED, border_style="cyan", show_header=False)
    menu.add_column("选项", style="bold green", width=4)
    menu.add_column("功能", style="white")
    menu.add_column("说明", style="dim")
    menu.add_row("[1]", "💬 开启新对话", "进入多轮对话模式（输入 quit 返回菜单）")
    menu.add_row("[2]", "📊 知识库状态", "查看 ChromaDB 各 collection 文档数")
    menu.add_row("[3]", "🔧 手动清理", "触发遗忘机制，清理低分文档")
    menu.add_row("[0]", "👋 退出程序", "")
    console.print(menu)
    console.print()
    return console.input("[bold cyan]  请选择 [0-3]> [/bold cyan]").strip()


async def show_kb_stats(vector_store):
    """知识库状态"""
    try:
        chat_count = vector_store.count("chat_history")
        docs_count = vector_store.count("travel_docs")
        prefs_count = vector_store.count("user_prefs")

        table = Table(title="📊 知识库状态", box=box.ROUNDED, border_style="green")
        table.add_column("Collection", style="cyan", width=25)
        table.add_column("用途", style="dim", width=30)
        table.add_column("文档数", style="bold green", width=10)
        table.add_row("chat_history", "用户对话摘要", str(chat_count))
        table.add_row("travel_docs", "搜索攻略缓存", str(docs_count))
        table.add_row("user_prefs", "用户偏好", str(prefs_count))
        console.print()
        console.print(table)
        console.print()
    except Exception as e:
        console.print(f"[red]知识库异常: {e}[/red]")


async def do_cleanup(forgetting_manager):
    """手动清理"""
    with console.status("[yellow]执行遗忘清理...[/yellow]"):
        result = await forgetting_manager.check_and_clean()
    console.print(f"\n[green]✅ 清理完成:[/green] 衰减 {result.get('decayed', 0)} | 压缩 {result.get('compressed', 0)} | 删除 {result.get('deleted', 0)}")
    console.print()


async def start_chat(agent, vector_store):
    """开启新对话"""
    from langchain_core.messages import HumanMessage, AIMessage

    console.print()
    console.print("[bold yellow]💬 新对话已开始[/bold yellow]")
    console.print("[dim]输入 quit / exit / q 返回主菜单[/dim]")
    console.print()

    chat_history: list = []
    turn = 0

    while True:
        turn += 1
        user_input = Prompt.ask(f"[bold cyan]  [{turn}][/bold cyan]").strip()

        if user_input.lower() in EXIT_WORDS:
            console.print("[dim]返回主菜单...[/dim]\n")
            return

        if not user_input:
            continue

        console.print()
        console.print(f"  [bold yellow]▶ 第 {turn} 轮 — 知识库: chat={vector_store.count('chat_history')}, docs={vector_store.count('travel_docs')}[/bold yellow]")
        console.print("  [dim]" + "─" * 50 + "[/dim]")
        console.print()

        chat_before = vector_store.count("chat_history")
        docs_before = vector_store.count("travel_docs")

        try:
            result = await agent.run(user_input, chat_history)
            plan = result.get("plan", "")

            chat_history.append(HumanMessage(content=user_input))
            if plan:
                chat_history.append(AIMessage(content=plan))

        except Exception as e:
            import traceback
            console.print(f"[red]❌ {e}[/red]")
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            continue

        # 显示知识库变化
        chat_after = vector_store.count("chat_history")
        docs_after = vector_store.count("travel_docs")
        delta_chat = chat_after - chat_before
        delta_docs = docs_after - docs_before

        console.print("  [dim]" + "─" * 50 + "[/dim]")
        status = f"✅ 第 {turn} 轮完成"
        if delta_chat > 0 or delta_docs > 0:
            status += f" | 📚 知识库: +{delta_chat}对话 +{delta_docs}文档 (chat={chat_after}, docs={docs_after})"
        console.print(f"  [bold green]{status}[/bold green]\n")

        if plan:
            # 路线图
            import re
            route_match = re.search(r"/static/route_[^\s\)]+\.html", plan)
            route_line = f"\n[green]🗺️  路线图:[/green] [underline]{route_match.group()}[/underline]" if route_match else ""

            console.print(Panel(
                plan,
                title=f"📋 Agent 回复 (第 {turn} 轮){route_line}",
                border_style="cyan",
            ))
        else:
            console.print("[yellow]⚠️  未生成回复[/yellow]")

        console.print("[dim]" + "=" * 50 + "[/dim]\n")


async def main():
    console.print(BANNER)

    with console.status("[bold green]初始化 Agent + ChromaDB...[/bold green]"):
        agent, vector_store, forgetting_manager = init_cli_agent()
    console.print("[green]✅ 初始化完成[/green]\n")

    while True:
        choice = await show_menu()

        if choice == "1":
            await start_chat(agent, vector_store)

        elif choice == "2":
            await show_kb_stats(vector_store)

        elif choice == "3":
            await do_cleanup(forgetting_manager)

        elif choice == "0":
            console.print("\n[green]👋 再见！[/green]")
            break

        else:
            console.print("[red]无效选项，请重试[/red]")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[green]👋 已中断，再见！[/green]")
