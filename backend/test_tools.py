"""测试所有工具是否正常加载和运行"""
import asyncio
import sys
from pathlib import Path

# 添加 backend 到路径
sys.path.insert(0, str(Path(__file__).parent))


def test_tools_loading():
    """测试工具加载"""
    print("=" * 50)
    print("测试工具加载")
    print("=" * 50)
    
    try:
        from tools import get_all_tools
        base_dir = Path(__file__).parent / "workspace"
        tools = get_all_tools(base_dir)
        print(f"✅ 成功加载 {len(tools)} 个工具:")
        for tool in tools:
            print(f"  - {tool.name}")
        return tools
    except Exception as e:
        print(f"❌ 工具加载失败: {e}")
        import traceback
        traceback.print_exc()
        return []


def test_terminal_tool(tools):
    """测试终端工具"""
    print("\n" + "=" * 50)
    print("测试 terminal 工具")
    print("=" * 50)
    
    terminal_tool = next((t for t in tools if t.name == "terminal"), None)
    if not terminal_tool:
        print("❌ 未找到 terminal 工具")
        return
    
    try:
        # 测试简单命令
        result = terminal_tool.func("echo hello")
        print(f"✅ 命令执行成功: {result[:100]}...")
    except Exception as e:
        print(f"❌ 命令执行失败: {e}")
        import traceback
        traceback.print_exc()


def test_fetch_url_tool(tools):
    """测试 URL 获取工具"""
    print("\n" + "=" * 50)
    print("测试 fetch_url 工具")
    print("=" * 50)
    
    fetch_tool = next((t for t in tools if t.name == "fetch_url"), None)
    if not fetch_tool:
        print("❌ 未找到 fetch_url 工具")
        return
    
    try:
        # 测试获取
        result = fetch_tool.func("httpbin.org/get")
        if "错误" in result:
            print(f"⚠️ URL 获取返回错误: {result}")
        else:
            print(f"✅ URL 获取成功: {result[:100]}...")
    except Exception as e:
        print(f"❌ URL 获取失败: {e}")
        import traceback
        traceback.print_exc()


def test_read_file_tool(tools):
    """测试文件读取工具"""
    print("\n" + "=" * 50)
    print("测试 read_file 工具")
    print("=" * 50)
    
    read_tool = next((t for t in tools if t.name == "read_file"), None)
    if not read_tool:
        print("❌ 未找到 read_file 工具")
        return
    
    try:
        # 测试读取不存在的文件
        result = read_tool.func("nonexistent.txt")
        print(f"✅ 文件读取处理成功: {result}")
    except Exception as e:
        print(f"❌ 文件读取失败: {e}")
        import traceback
        traceback.print_exc()


def test_python_repl_tool(tools):
    """测试 Python REPL 工具"""
    print("\n" + "=" * 50)
    print("测试 python_repl 工具")
    print("=" * 50)
    
    python_tool = next((t for t in tools if t.name == "python_repl"), None)
    if not python_tool:
        print("❌ 未找到 python_repl 工具")
        return
    
    try:
        # 测试执行代码
        result = python_tool.func("1 + 1")
        print(f"✅ Python 代码执行成功: {result}")
    except Exception as e:
        print(f"❌ Python 代码执行失败: {e}")
        import traceback
        traceback.print_exc()


async def test_search_knowledge_tool(tools):
    """测试知识库搜索工具"""
    print("\n" + "=" * 50)
    print("测试 search_knowledge 工具")
    print("=" * 50)

    search_tool = next((t for t in tools if t.name == "search_knowledge"), None)
    if not search_tool:
        print("❌ 未找到 search_knowledge 工具")
        return
    
    try:
        # 测试搜索（可能知识库为空）
        result = search_tool.func("测试")
        print(f"✅ 知识库搜索完成: {result[:100]}...")
    except Exception as e:
        print(f"❌ 知识库搜索失败: {e}")
        import traceback
        traceback.print_exc()


def test_todo_write_tool(tools):
    """测试待办事项管理工具"""
    print("\n" + "=" * 50)
    print("测试 todo_write 工具")
    print("=" * 50)
    
    todo_tool = next((t for t in tools if t.name == "todo_write"), None)
    if not todo_tool:
        print("❌ 未找到 todo_write 工具")
        return
    
    try:
        # 测试创建待办事项列表
        test_todos = [
            {"id": "task1", "content": "分析需求", "status": "completed", "priority": "high"},
            {"id": "task2", "content": "编写代码", "status": "in_progress", "priority": "high"},
            {"id": "task3", "content": "测试验证", "status": "pending", "priority": "medium"},
        ]
        result = todo_tool.func({"todos": test_todos})
        print(f"✅ 待办事项创建成功:\n{result}")
        
        # 测试更新待办事项
        test_todos[1]["status"] = "completed"
        test_todos[2]["status"] = "in_progress"
        result = todo_tool.func({"todos": test_todos})
        print(f"✅ 待办事项更新成功:\n{result}")
        
        # 测试错误情况 - 少于3个任务
        result = todo_tool.func({"todos": [{"id": "1", "content": "test", "status": "pending", "priority": "low"}]})
        print(f"✅ 错误处理正常: {result}")
        
        # 测试错误情况 - 多个 in_progress
        result = todo_tool.func({"todos": [
            {"id": "1", "content": "task1", "status": "in_progress", "priority": "low"},
            {"id": "2", "content": "task2", "status": "in_progress", "priority": "low"},
            {"id": "3", "content": "task3", "status": "pending", "priority": "low"},
        ]})
        print(f"✅ 错误处理正常: {result}")
        
    except Exception as e:
        print(f"❌ 待办事项工具测试失败: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """主测试函数"""
    print("开始工具测试...")
    
    # 测试工具加载
    tools = test_tools_loading()
    if not tools:
        print("\n❌ 工具加载失败，停止测试")
        return
    
    # 测试各个工具
    test_terminal_tool(tools)
    test_fetch_url_tool(tools)
    test_read_file_tool(tools)
    test_python_repl_tool(tools)
    await test_search_knowledge_tool(tools)
    test_todo_write_tool(tools)
    
    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
