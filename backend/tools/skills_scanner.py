"""技能目录扫描器"""
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import yaml

from utils.logger import get_logger

logger = get_logger("SkillsScanner")


def parse_frontmatter(content: str) -> tuple[Dict[str, Any], str]:
    """解析 Markdown frontmatter"""
    # 匹配 --- 包裹的 YAML
    pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
    match = re.match(pattern, content, re.DOTALL)
    
    if match:
        try:
            frontmatter = yaml.safe_load(match.group(1))
            body = match.group(2)
            return frontmatter or {}, body
        except Exception:
            pass
    
    return {}, content


def scan_skills(skills_dir: Path) -> List[Dict[str, Any]]:
    """扫描技能目录"""
    skills = []
    
    if not skills_dir.exists():
        return skills
    
    for skill_dir in skills_dir.iterdir():
        if not skill_dir.is_dir():
            continue
        
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue
        
        try:
            content = skill_file.read_text(encoding="utf-8")
            frontmatter, body = parse_frontmatter(content)
            
            skill_info = {
                "name": frontmatter.get("name", skill_dir.name),
                "description": frontmatter.get("description", ""),
                "location": f"workspace/skills/{skill_dir.name}/SKILL.md"
            }
            skills.append(skill_info)
            
        except Exception as e:
            logger.warning(f"读取技能失败 {skill_file}: {e}")
    
    return skills


def generate_skills_snapshot(skills: List[Dict[str, Any]], output_path: Path):
    """生成技能快照文件"""
    lines = ["<!-- Skills Snapshot - 自动生成，请勿手动编辑 -->", ""]
    lines.append("<available_skills>")
    
    for skill in skills:
        lines.append("  <skill>")
        lines.append(f"    <name>{skill['name']}</name>")
        lines.append(f"    <description>{skill['description']}</description>")
        lines.append(f"    <location>{skill['location']}</location>")
        lines.append("  </skill>")
    
    lines.append("</available_skills>")
    
    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"生成快照: {output_path} ({len(skills)} 个技能)")


def scan_and_generate_snapshot(base_dir: Path) -> List[Dict[str, Any]]:
    """扫描并生成技能快照"""
    skills_dir = base_dir / "workspace" / "skills"
    output_path = base_dir / "SKILLS_SNAPSHOT.md"
    
    skills = scan_skills(skills_dir)
    generate_skills_snapshot(skills, output_path)
    
    return skills
