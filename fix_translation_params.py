#!/usr/bin/env python3
"""
Fix parameter names in translation files to match English template.
"""

import json
import re
from pathlib import Path

def fix_translation_parameters():
    """Fix parameter name mismatches in translation files."""
    
    translations_dir = Path("translations")
    
    # Parameter mappings (Spanish translation -> English original)
    param_fixes = {
        "spanish_prompts.json": {
            # Constraint re-prompt
            "{nombre_del_participante}": "{participant_name}",
            "{nombre_del_principio}": "{principle_name}",
            "{tipo_de_restricción}": "{constraint_type}",
            
            # Other parsing prompts
            "{respuesta}": "{response}",
            "{afirmación}": "{statement}",
            
            # Context formatting
            "{nombre}": "{name}",
            "{descripción_del_papel}": "{role_description}",
            "{fase}": "{phase}",
            "{número_de_ronda}": "{round_number}",
            "{memoria_formateada}": "{formatted_memory}",
            "{experimento_explicacion}": "{experiment_explanation}",
            "{personalidad}": "{personality}",
            "{instrucciones_de_fase}": "{phase_instructions}",
            "{memoria}": "{memory}",
            
            # Phase 2 instructions
            "{número_ronda}": "{round_number}",
        },
        "mandarin_prompts.json": {
            # Context formatting parameters
            "{记忆}": "{memory}",
            "{姓名}": "{name}",
            "{角色描述}": "{role_description}",
            "{相位指示}": "{phase_instructions}",
            "{格式化内存}": "{formatted_memory}",
            "{实验说明}": "{experiment_explanation}",
            "{个性}": "{personality}",
            
            # Parsing parameters
            "{回答}": "{response}",
            "{声明}": "{statement}",
            "{陈述}": "{statement}",
            
            # Other parameters that may have been translated
            "{participant_name}": "{participant_name}",
            "{principle_name}": "{principle_name}",
            "{constraint_type}": "{constraint_type}",
            "{round_number}": "{round_number}",
            "{轮数}": "{round_number}",
            "{回合数}": "{round_number}",
            "{约束_类型}": "{constraint_type}",
            "{回应}": "{response}",
            "{答复}": "{response}",
            
            # Fix broken duplicates and formatting issues
            "姓名：姓名": "姓名：{name}",
            "角色描述：角色描述： {role_description}": "角色描述：{role_description}",
            "当前阶段：当前阶段： {phase}": "当前阶段：{phase}",
            "{相位指示}{相位指示": "{phase_instructions}",
        }
    }
    
    for filename, fixes in param_fixes.items():
        filepath = translations_dir / filename
        if not filepath.exists():
            continue
            
        print(f"Fixing parameters in {filename}...")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Apply fixes
        for wrong_param, correct_param in fixes.items():
            if wrong_param in content:
                content = content.replace(wrong_param, correct_param)
                print(f"  Fixed: {wrong_param} -> {correct_param}")
        
        # Write back
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"  ✓ {filename} updated")
    
    print("\n✅ All translation parameter fixes completed!")

if __name__ == "__main__":
    fix_translation_parameters()