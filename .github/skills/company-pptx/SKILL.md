---
name: company-pptx
description: "生成公司标准风格的 PPTX 演示文稿（基于 GPDI 模板）。触发词：生成PPT, 生成演示文稿, 生成汇报, 生成提案, 公司PPT, 工作汇报PPT, 项目汇报PPT, 技术方案PPT, 投标PPT, 可研PPT, 项目建议书PPT, 年度报告PPT, GPDI风格. 使用公司视觉规范（红色系 #CC0000 + 灰色 #808080）和 Microsoft YaHei 字体。输出前必须执行检查清单。"
---

# 公司专用 PPTX 生成规范（GPDI 风格）

## 1. 定位与适用范围

本 skill 适用于所有需要**以公司名义对外交付**的演示文稿，包括但不限于：
- 工作汇报（年度/季度/专项）
- 项目建议书、技术方案
- 投标演示、可研汇报
- 对领导/甲方的提案展示

---

## 2. 模板文件

**GPDI 模板路径**（优先使用）：
```
C:\Users\lucky\Desktop\附件1：2026年GPDI工作报告PPT模板.pptx
```

**模板结构**（6页，可按需扩展）：
| 页号 | 用途 | Layout |
|------|------|--------|
| S1 | 封面（底图全幅+标题+副标题） | 标题幻灯片 |
| S2 | 目录（5条目，组合图标） | 仅标题 |
| S3-S5 | 内容页（空白区，自由排版） | 仅标题 |
| S6 | 结束页（全幅背景+Logo） | 仅标题 |

**备用基线模板**（岭南样例，富元素）：
```
C:\Users\lucky\Documents\WXWork\1688853513781559\Cache\File\2026-04\pptx\pptx\岭南国家公园_项目建议书_送审版_样例.pptx
```

---

## 3. 公司视觉规范（必须遵守）

### 配色系统

| 角色 | 色值 | 使用场景 |
|------|------|----------|
| **品牌红（主色）** | `#CC0000` | 标题条、强调色块、数字高亮 |
| **深红** | `#C00000` | 表格表头、图表主系列 |
| **中灰** | `#808080` | 副标题、辅助线、次要说明 |
| **深灰文字** | `#404040` | 正文、列表 |
| **浅灰底** | `#F5F5F5` | 内容卡片背景 |
| **白色** | `#FFFFFF` | 封面文字、标题条文字 |
| **黑色** | `#000000` | 表格数据、注释 |

> ⚠️ **禁用**：蓝色系（`#1E2761`/`#4F81BD`）、绿色系——这是旧样例的色板，GPDI 模板不使用。

### 字体规范

| 元素 | 字体 | 字号 | 样式 |
|------|------|------|------|
| 封面主标题 | Microsoft YaHei | 32-36pt | Bold，白色 |
| 封面副标题 | Microsoft YaHei | 18-20pt | Regular，白色或浅灰 |
| 章节标题（红色条） | Microsoft YaHei | 20-24pt | Bold，白色 |
| 页面二级标题 | Microsoft YaHei | 16-18pt | Bold，`#CC0000` 或深灰 |
| 正文/要点 | Microsoft YaHei | 13-14pt | Regular，`#404040` |
| 表格表头 | Microsoft YaHei | 12-13pt | Bold，白色底红 |
| 表格数据 | Microsoft YaHei | 11-12pt | Regular |
| 页码/注释 | Microsoft YaHei | 10pt | Regular，灰色 |

### 页面尺寸
- **宽度**：10,972,800 EMU（≈11.11英寸 / 28.22cm）
- **高度**：6,172,200 EMU（≈6.25英寸 / 15.88cm）
- 对应代码：`prs.slide_width = Emu(10972800); prs.slide_height = Emu(6172200)`

---

## 4. 工作流（双路径）

### 路径 A：基于 GPDI 模板的 python-pptx 替换（推荐）

适用于：内容结构与模板高度匹配时（封面+目录+内容页+结尾）。

```python
# 标准流程
from pptx import Presentation
from pptx.util import Emu, Pt
from pptx.dml.color import RGBColor

prs = Presentation(r"C:\Users\lucky\Desktop\附件1：2026年GPDI工作报告PPT模板.pptx")

# 替换文字（保留格式）
def safe_set_run_text(shape, new_text):
    """格式保留式单次文字替换"""
    tf = shape.text_frame
    if not tf.paragraphs or not tf.paragraphs[0].runs:
        return
    first_run = tf.paragraphs[0].runs[0]
    # 清除多余段落和 run
    from lxml import etree
    txBody = tf._txBody
    for p in list(txBody)[1:]:
        if p.tag.endswith('}p'):
            txBody.remove(p)
    p0 = txBody.findall('.//{http://schemas.openxmlformats.org/drawingml/2006/main}p')[0]
    for r in p0.findall('.//{http://schemas.openxmlformats.org/drawingml/2006/main}r')[1:]:
        p0.remove(r)
    first_run.text = new_text
```

### 路径 B：pptx skill XML 管道（高度自定义时）

适用于：需要大幅度结构改动、多页扩展、动态内容页时。

```bash
SCRIPTS=C:/Users/lucky/Documents/WXWork/1688853513781559/Cache/File/2026-04/pptx/pptx/scripts

# 1. 解包
python $SCRIPTS/office/unpack.py "C:\Users\lucky\Desktop\附件1：2026年GPDI工作报告PPT模板.pptx" unpacked/

# 2. 按需复制内容页
python $SCRIPTS/add_slide.py unpacked/ slide3.xml   # 复制 S3 作为新内容页

# 3. 编辑 unpacked/ppt/slides/slide*.xml（直接改 XML）

# 4. 清理
python $SCRIPTS/clean.py unpacked/

# 5. 打包
python $SCRIPTS/office/pack.py unpacked/ output.pptx --original "C:\Users\lucky\Desktop\附件1：2026年GPDI工作报告PPT模板.pptx"
```

---

## 5. 标准版式骨架

### 5.1 封面页（S1）
- 全幅背景图（模板 image4.png，872KB，深色商务摄影）
- 中心白色半透明圆角矩形（可选）承载标题
- 主标题：项目/报告全称，36pt Bold，白色
- 副标题：单位名 + 日期，18pt，白色/浅灰

### 5.2 目录页（S2）
- 顶部红色标题条（全宽 × 1.9cm 高）+ 白色"目  录"字样
- 5个纵向条目组（组合图标），从上到下等间距排列
- 每条目：序号圆（红底白字）+ 章节名称文字
- 中间水平分割线（`#CC0000`，0.5pt）

### 5.3 内容页（S3-S5，可复制扩展）
- 顶部标题条（红底 `#CC0000`，全宽 × 1.9cm）+ 章节标题（白色 Bold）
- 内容区（标题条下方至页面底部），支持以下版式：
  - **版式A 双栏**：两个宽度各 13cm 的白色圆角卡片，细灰边框
  - **版式B 单栏+表格**：文字描述 + 数据表（红底表头）
  - **版式C 三块**：3个等宽卡片，顶部小红色标签
  - **版式D 流程图**：横向箭头流程，每步骤为红边白底圆角矩形
  - **版式E 大数字突出**：2-4个数据卡，数字 48pt 红色，说明 12pt 灰色

### 5.4 结束页（S6）
- 全幅背景图（模板 image4.png）
- 居中文字："谢  谢！" 或 "感谢聆听"，36pt Bold，白色
- 右下角公司 Logo（模板 image2.png）

---

## 6. 代码生成规范

### 必须在代码开头定义的颜色常量
```python
# 公司配色常量
RED_PRIMARY   = RGBColor(0xCC, 0x00, 0x00)  # #CC0000 品牌红
RED_DEEP      = RGBColor(0xC0, 0x00, 0x00)  # #C00000 深红
GRAY_MID      = RGBColor(0x80, 0x80, 0x80)  # #808080 中灰
GRAY_TEXT     = RGBColor(0x40, 0x40, 0x40)  # #404040 正文深灰
GRAY_BG       = RGBColor(0xF5, 0xF5, 0xF5)  # #F5F5F5 浅灰底
WHITE         = RGBColor(0xFF, 0xFF, 0xFF)  # #FFFFFF
BLACK         = RGBColor(0x00, 0x00, 0x00)  # #000000
FONT_CN       = "Microsoft YaHei"           # 唯一字体
```

### 输出文件命名规范
```
{项目名}_{文档类型}_{日期}_v{版本}.pptx
# 例如：岭南国家公园_工作汇报_20260416_v1.pptx
```

---

## 7. 完成检查清单（必须全部通过）

在输出 PPTX 前，运行以下检查：

```python
# 检查脚本骨架
from pptx import Presentation

def audit_pptx(path):
    prs = Presentation(path)
    errors = []

    for si, slide in enumerate(prs.slides, 1):
        for shape in slide.shapes:
            # 1. 字体一致性
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    for run in para.runs:
                        if run.font.name and run.font.name not in ("Microsoft YaHei", "+mn-lt", "+mj-lt", None):
                            errors.append(f"S{si}/{shape.name}: 非标字体 {run.font.name}")

            # 2. 文字出框检测（简单版：shape 在页面外）
            if shape.left is not None:
                lft = shape.left / 914400 * 2.54
                if lft > 29 or lft < -1:
                    errors.append(f"S{si}/{shape.name}: 形状超出页面 left={lft:.1f}cm")

    if errors:
        print(f"发现 {len(errors)} 个问题：")
        for e in errors:
            print(f"  ❌ {e}")
    else:
        print("✅ 检查通过，零问题")
    return len(errors) == 0
```

### 人工目检要点
- [ ] 每页标题条颜色是否为 `#CC0000`（非蓝色）
- [ ] 字体是否为微软雅黑（非 Arial、宋体、Calibri）
- [ ] 文字是否出框或被裁切
- [ ] 表格是否有红底白字表头
- [ ] 封面和结尾背景图是否完整显示
- [ ] 页码是否正确（S2-S6 右下角）
- [ ] 结束页公司 Logo 是否可见

---

## 8. 与 tender-doc-delivery skill 的关系

| 场景 | 使用哪个 skill |
|------|---------------|
| 生成 Word 正式文档（可研/标书/方案） | `tender-doc-delivery` |
| 生成对外交付 PPTX（汇报/提案/投标） | **本 skill（company-pptx）** |
| 同一项目既要 Word 又要 PPT | 两者配合使用，内容互引 |

> 本 skill 依赖 pptx 处理库：`pip install python-pptx lxml`

---

## 9. 常见问题

**Q: 内容页需要超过 3 页怎么办？**  
A: 用路径B（XML管道）的 `add_slide.py` 复制 S3 模板页，然后逐页编辑内容。

**Q: 需要插入图表（柱状图/折线图）怎么办？**  
A: 用 python-pptx 的 `chart` API，主系列色用 `#CC0000`，次系列用 `#808080`。

**Q: 模板文件不在桌面怎么办？**  
A: 在项目 `output/` 目录同级放置一份副本，或更新 skill 中的路径。
