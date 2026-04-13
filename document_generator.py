"""
文档模板生成器
用法: py document_generator.py [模板类型] [项目名称]
模板类型: 1=可研, 2=技术方案, 3=标书应答
"""

import os
from datetime import datetime

TEMPLATES_DIR = r"C:\Users\lucky\projects\my_project\templates"
OUTPUT_DIR = r"C:\Users\lucky\projects\my_project\output\documents"

TEMPLATE_STRUCTURES = {
    "1": {
        "name": "可行性研究报告",
        "chapters": [
            "第一章 项目概述",
            "第二章 需求分析",
            "第三章 建设方案",
            "第四章 项目选址与建设条件",
            "第五章 投资估算",
            "第六章 效益分析",
            "第七章 结论与建议"
        ]
    },
    "2": {
        "name": "技术方案",
        "chapters": [
            "第一章 项目概述",
            "第二章 现状分析",
            "第三章 总体设计",
            "第四章 详细设计",
            "第五章 技术选型",
            "第六章 实施方案",
            "第七章 运维保障",
            "第八章 验收标准",
            "第九章 报价清单"
        ]
    },
    "3": {
        "name": "标书技术应答",
        "chapters": [
            "技术响应函",
            "第一章 项目概述",
            "第二章 现有条件分析",
            "第三章 技术方案",
            "第四章 项目实施方案",
            "第五章 售后服务",
            "附件：资质证明"
        ]
    }
}

def generate_document(template_type: str, project_name: str, output_path: str = None) -> str:
    """生成文档框架"""
    
    if template_type not in TEMPLATE_STRUCTURES:
        raise ValueError(f"无效的模板类型: {template_type}")
    
    template = TEMPLATE_STRUCTURES[template_type]
    today = datetime.now().strftime("%Y-%m-%d")
    
    content = f"""# {project_name} {template['name']}

> 生成时间: {today}
> 自动生成框架，待填充内容

---

""".encode('utf-8').decode('utf-8')
    
    # Windows 中文编码处理
    content = f"""# {project_name} {template['name']}

> 生成时间: {today}
> 自动生成框架，待填充内容

---

"""
    
    for i, chapter in enumerate(template["chapters"], 1):
        content += f"## {chapter}\n\n"
        content += "（待补充内容）\n\n---\n\n"
    
    # 输出文件
    if output_path is None:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        filename = f"{today}_{project_name}_{template['name']}.md"
        output_path = os.path.join(OUTPUT_DIR, filename)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return output_path

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("用法: py document_generator.py [模板类型] [项目名称]")
        print("模板类型: 1=可研, 2=技术方案, 3=标书应答")
        print("示例: py document_generator.py 1 某市政府信息化项目")
        sys.exit(1)
    
    template_type = sys.argv[1]
    project_name = sys.argv[2]
    
    try:
        output_path = generate_document(template_type, project_name)
        print(f"✅ 文档已生成: {output_path}")
    except Exception as e:
        print(f"❌ 错误: {e}")
