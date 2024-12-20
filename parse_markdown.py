import os
import re

class MarkdownEntity:
    def __init__(self, content: str = "", entity_type: str = ""):
        self.content = content
        self.entity_type = entity_type

    def __repr__(self):
        return f'<{self.entity_type}: {repr(self.content)}>'

    def copy(self):
        return self.__class__(self.content)

class TitleEntity(MarkdownEntity):
    def __init__(self, content: str = "", level: int = 1):
        super().__init__(content, 'TitleEntity')
        self.level = level

class CodeBlock(MarkdownEntity):
    def __init__(self, content: str = "", language: str = 'python', delimiter: str = '```'):
        super().__init__(content, 'CodeBlock')
        self.language = language
        self.delimiter = delimiter

class ListItem(MarkdownEntity):
    def __init__(self, content: str = ""):
        super().__init__(content, 'ListItem')

class LinkEntity(MarkdownEntity):
    def __init__(self, content: str = "", url: str = ""):
        super().__init__(content, 'LinkEntity')
        self.url = url

class ImageEntity(MarkdownEntity):
    def __init__(self, content: str = "", url: str = ""):
        super().__init__(content, 'ImageEntity')
        self.url = url
        self.alt_text = content

class EmptyLine(MarkdownEntity):
    def __init__(self, content: str = ""):
        super().__init__(content, 'EmptyLine')

class Text(MarkdownEntity):
    def __init__(self, content: str = ""):
        super().__init__(content, 'Text')

class CompositeEntity(MarkdownEntity):
    def __init__(self, content: str = "", entity_type: str = ""):
        super().__init__(content, entity_type)
        self.children = []

    def add_child(self, child):
        self.children.append(child)

class ListItem(CompositeEntity):
    def __init__(self, content: str = "", level: int = 0):
        super().__init__(content, 'ListItem')
        self.level = level
        if content:
            self.parse_content()

    def parse_content(self):
        inline_elements = parse_inline_elements(self.content)
        for elem in inline_elements:
            if isinstance(elem, str):
                self.add_child(Text(elem))
            else:
                self.add_child(elem)

class OrderedListItem(ListItem):
    def __init__(self, content: str = "", level: int = 0, index: int = 1):
        super().__init__(content, level)
        self.entity_type = 'OrderedListItem'
        self.index = index

class UnorderedListItem(ListItem):
    def __init__(self, content: str = "", level: int = 0):
        super().__init__(content, level)
        self.entity_type = 'UnorderedListItem'

class DisplayMath(MarkdownEntity):
    def __init__(self, content: str = ""):
        super().__init__(content, 'DisplayMath')

class InlineLink(MarkdownEntity):
    def __init__(self, content: str = "", url: str = ""):
        super().__init__(content, 'InlineLink')
        self.url = url

class InlineMath(MarkdownEntity):
    def __init__(self, content: str = ""):
        super().__init__(content, 'InlineMath')

class Paragraph(CompositeEntity):
    def __init__(self, content: str = ""):
        super().__init__(content, 'Paragraph')
        if content:
            self.parse_content()

    def parse_content(self):
        inline_elements = parse_inline_elements(self.content)
        for elem in inline_elements:
            if isinstance(elem, str):
                self.add_child(Text(elem))
            else:
                self.add_child(elem)

    def __repr__(self):
        return f'<Paragraph: {repr(self.children)}>'

def parse_inline_elements(text):
    elements = []
    current_text = ""

    i = 0
    while i < len(text):
        if text[i:i+2] == '$$':  # Display math
            if current_text:
                elements.append(Text(current_text))
                current_text = ""
            end = text.find('$$', i+2)
            if end != -1:
                elements.append(DisplayMath(text[i+2:end]))
                i = end + 2
            else:
                current_text += text[i:]
                break
        elif text[i] == '$':  # Inline math
            if current_text:
                elements.append(Text(current_text))
                current_text = ""
            end = text.find('$', i+1)
            if end != -1:
                elements.append(InlineMath(text[i+1:end]))
                i = end + 1
            else:
                current_text += text[i:]
                break
        elif text[i] == '[':  # 潜在的链接
            if current_text:
                elements.append(Text(current_text))
                current_text = ""

            # 查找匹配的右括号
            bracket_count = 1
            j = i + 1
            while j < len(text) and bracket_count > 0:
                if text[j] == '[':
                    bracket_count += 1
                elif text[j] == ']':
                    bracket_count -= 1
                j += 1

            if j < len(text) and text[j] == '(':
                # 找到了有效的链接格式
                content_end = j - 1
                url_start = j + 1
                url_end = text.find(')', url_start)
                if url_end != -1:
                    content = text[i+1:content_end]
                    url = text[url_start:url_end]
                    elements.append(InlineLink(content, url))
                    i = url_end + 1
                    continue

            # 如果不是有效的链接格式，将其作为普通文本处理
            current_text += text[i]
            i += 1
        else:
            current_text += text[i]
            i += 1

    if current_text:
        elements.append(Text(current_text))

    return elements

def parse_markdown(lines, delimiter='\n'):
    entities = []
    current_code_block = []
    current_math_block = []
    in_code_block = False
    in_math_block = False
    language = ""
    code_delimiter = ""

    for line in lines:
        if line == delimiter:
            continue
        if line.startswith('$$') and not in_code_block:
            if in_math_block:
                entities.append(DisplayMath('\n'.join(current_math_block)))
                current_math_block = []
                in_math_block = False
            else:
                in_math_block = True
        elif in_math_block:
            current_math_block.append(line)
        elif line.startswith('#') and not in_code_block and not in_math_block:
            level = line.count('#')
            title_content = line[level:].strip()
            entities.append(TitleEntity(title_content, level))
        elif line.startswith('```') or line.startswith('~~~'):  # 支持两种代码块分隔符
            if in_code_block:
                if not line.startswith(code_delimiter):
                    current_code_block.append(line)
                    continue
                entities.append(CodeBlock('\n'.join(current_code_block), language, code_delimiter))
                current_code_block = []
                in_code_block = False
                language = ""
                code_delimiter = None
            else:
                in_code_block = True
                code_delimiter = '```' if line.startswith('```') else '~~~'  # 记录使用的分隔符
                language = line.lstrip('`').lstrip('~').strip()
        elif in_code_block:
            current_code_block.append(line)
        elif '[' in line and ']' in line and '(' in line and ')' in line and line.count('[') == 1 and line.strip().endswith(')') and line.strip().startswith('[') and line.count('!') == 0:
            start = line.index('[') + 1
            end = line.index(']')
            url_start = line.index('(') + 1
            url_end = line.index(')')
            link_text = line[start:end].strip()
            link_url = line[url_start:url_end].strip()
            entities.append(LinkEntity(link_text, link_url))
        elif '[' in line and ']' in line and '(' in line and ')' in line and line.count('[') == 1 and line.strip().endswith(')') and line.strip().startswith('![') and line.count('!') == 1:
            start = line.index('[') + 1
            end = line.index(']')
            url_start = line.index('(') + 1
            url_end = line.index(')')
            link_text = line[start:end].strip()
            link_url = line[url_start:url_end].strip()
            entities.append(ImageEntity(link_text, link_url))
        else:
            # Check for list items
            list_match = re.match(r'^(\s*)([*+-]|\d+\.)\s(.+)$', line)
            if list_match:
                indent, list_type, content = list_match.groups()
                level = len(indent) // 2  # Assuming 2 spaces per indent level

                if list_type in ['*', '-', '+']:
                    list_item = UnorderedListItem(content, level)
                else:
                    index = int(list_type[:-1])
                    list_item = OrderedListItem(content, level, index)

                entities.append(list_item)

            elif line.strip():
                # 处理其他内容(段落、链接等)
                inline_elements = parse_inline_elements(line)
                para = Paragraph()
                for elem in inline_elements:
                    if isinstance(elem, str):
                        para.add_child(Text(elem))
                        para.content += elem
                    else:
                        para.add_child(elem)
                        para.content += convert_entity_to_text(elem)
                entities.append(para)
            else:
                entities.append(EmptyLine(line))

    # 处理文档末尾可能未闭合的数学公式块
    if in_math_block:
        entities.append(DisplayMath(''.join(current_math_block)))

    return entities

def convert_entity_to_text(entity, indent='', linemode=False):
    if isinstance(entity, TitleEntity):
        return f"{'#' * entity.level} {entity.content}"
    elif isinstance(entity, CodeBlock):
        code = entity.content.lstrip('\n')
        return f"{entity.delimiter}{entity.language}\n{code}\n{entity.delimiter}"
    elif isinstance(entity, OrderedListItem) and linemode:
        return f"{indent}{entity.index}. {entity.content}"
    elif isinstance(entity, UnorderedListItem) and linemode:
        return f"{indent}- {entity.content}"
    elif isinstance(entity, (OrderedListItem, UnorderedListItem)) and not linemode:
        prefix = f"{entity.level * 2 * ' '}{entity.index}. " if isinstance(entity, OrderedListItem) else f"{entity.level * 2 * ' '}- "
        content = convert_entities_to_text(entity.children, inline=True)
        return f"{prefix}{content}"
    elif isinstance(entity, LinkEntity):
        return f"[{entity.content}]({entity.url})"
    elif isinstance(entity, ImageEntity):
        return f"![{entity.content}]({entity.url})"
    elif isinstance(entity, InlineLink):
        return f"[{entity.content}]({entity.url})"
    elif isinstance(entity, EmptyLine):
        return f"{entity.content}"
    elif isinstance(entity, Text):
        return f"{entity.content}"
    elif isinstance(entity, Paragraph):
        return entity.content
        # return convert_entities_to_text(entity.children, inline=True)
    elif isinstance(entity, DisplayMath):
        return f"$$\n{entity.content}\n$$"
    elif isinstance(entity, InlineMath):
        return f"${entity.content}$"
    elif isinstance(entity, CompositeEntity):
        if linemode:
            return entity.content
        else:
            return convert_entities_to_text(entity.children, indent, inline=True)
    else:
        return str(entity)

def convert_entities_to_text(entities, indent='', inline=False, linemode=False):
    result = []
    for index, entity in enumerate(entities):
        # print("entity", entity)
        converted = convert_entity_to_text(entity, indent, linemode=linemode)
        if inline:
            result.append(converted)
        elif index != len(entities) - 1 or (index == len(entities) - 1 and isinstance(entities[-1], EmptyLine)):
            result.append(converted + '\n')
        else:
            result.append(converted)

    if result[-1] == '\n':
        result = result[:-1]
    if inline:
        return ''.join(result).rstrip()
    else:
        return ''.join(result)

def save_text_to_file(text: str, file_path: str):
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(text)

def process_markdown_entities_and_save(entities, file_path, raw_text=None, linemode=False):
    # Step 1: Convert entities to text
    text_output = convert_entities_to_text(entities, linemode=linemode)
    if raw_text and raw_text != text_output:
        raise ValueError("The text output does not match the raw text input.")
    # Step 2: Save to file
    save_text_to_file(text_output, file_path)

def read_markdown_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        # 如果文件不存在，创建一个空文件
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as file:
            pass  # 创建一个空文件
        return ""  # 返回空字符串

def split_markdown(text, delimiter='\n'):
    # 使用两个换行符作为分割标记，分割段落
    # 创建一个新的列表来存储结果
    paragraphs = text.split(delimiter)
    # print(paragraphs)
    result = []

    # 遍历分割后的段落，在它们之间插入空行实体
    for i, paragraph in enumerate(paragraphs):
        if i > 0:
            # 在非第一段之前插入空行实体
            result.append(delimiter)

        # 添加当前段落
        result.append(paragraph)
    # print(result)

    return result

def get_entities_from_markdown_file(file_path, delimiter='\n', raw_text=None):
    # 读取 Markdown 文件
    if raw_text == None:
        markdown_text = read_markdown_file(file_path)
        if markdown_text == "":
            return []
    else:
        markdown_text = raw_text

    # 分割 Markdown 文档
    paragraphs = split_markdown(markdown_text, delimiter=delimiter)

    # 解析 Markdown 文档
    return parse_markdown(paragraphs, delimiter=delimiter)

def check_markdown_parse(markdown_file_path, output_file_path="output.md", delimiter='\n', debug=False):
    # 读取 Markdown 文件
    markdown_text = read_markdown_file(markdown_file_path)

    # 分割 Markdown 文档
    paragraphs = split_markdown(markdown_text, delimiter=delimiter)

    # 解析 Markdown 文档
    parsed_entities = parse_markdown(paragraphs, delimiter=delimiter)
    if debug:
        # print(parsed_entities)
        for entity in parsed_entities:
            print(entity)
            if hasattr(entity, 'children'):
                for child in entity.children:
                    print("child", child)

    # 将解析结果转换为文本
    converted_text = convert_entities_to_text(parsed_entities)

    # 检查原始文本和转换后的文本是否相同
    # print(converted_text)
    if markdown_text != converted_text:
        save_text_to_file(converted_text, output_file_path)
        raise ValueError("The converted text does not match the original text.")

    return parsed_entities

if __name__ == '__main__':
    # markdown_file_path = "README_CN.md"  # 替换为你的 Markdown 文件路径

    # # 读取 Markdown 文件
    # markdown_text = read_markdown_file(markdown_file_path)
    # paragraphs = split_markdown(markdown_text)
    # parsed_entities = parse_markdown(paragraphs)

    # # # 显示解析结果
    # # result = [str(entity) for entity in parsed_entities]
    # # for idx, entity in enumerate(result):
    # #     print(f"段落 {idx + 1} 解析：{entity}\n")

    # # 保存到文件
    # output_file_path = "output.md"
    # process_markdown_entities_and_save(parsed_entities, output_file_path, raw_text=markdown_text)

    # print(f"Markdown 文档已保存到 {output_file_path}")
    # check_markdown_parse("/Users/yanyuming/Downloads/GitHub/PurePage/index.md", "output.md")
    check_markdown_parse("/Users/yanyuming/Downloads/GitHub/PurePage/post/ViT/index.md", "output.md")
    # check_markdown_parse("/Users/yanyuming/Downloads/GitHub/xue/README.md", "output.md")