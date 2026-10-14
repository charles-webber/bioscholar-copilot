from dataclasses import dataclass

@dataclass
class PolicyDecision:
    allowed:bool
    reason:str
    next_action:str


HIGH_RISK_TERMS=(
    "制造病原体",
    "扩增病原体",
    "提高毒力",
    "增强传播",
    "人体注射",
    "人体实验",
    "绕过伦理审批",
    "窃取患者数据",
    "泄露患者隐私",
)

CLINICAL_DECISION_TERMS=(
    "我是不是得了",
    "帮我诊断",
    "直接开药",
    "停药",
    "改变剂量",
    "替代医生",
)

UNSAFE_MODEL_OUTPUT_TERMS = (
    "你应该停药",
    "你应当停药",
    "建议立即停药",
    "剂量调整为",
    "每天服用",
    "每次服用",
    "我诊断你",
    "你已确诊",
    "按以下步骤制造病原体",
    "按以下步骤增强传播",
    "绕过伦理审批的方法",
)

def contains_any(
    text:str,
    terms:tuple[str,...],
)->bool:
    """只要出现任意一个词就返回 True。"""
    return any(term in text for term in terms)

def is_ethics_evasion(text:str)->bool:
    """识别绕过或规避伦理审查的组合表达。"""
    evasion_terms=("绕过", "规避", "不经过")
    ethics_terms=("伦理审批", "伦理审查")
    return contains_any(
        text,
        evasion_terms,
    ) and contains_any(text,ethics_terms)

def is_pathogen_enhancement(text:str)->bool:
    """识别增强病原体危险属性的组合表达。"""
    enhancement_terms=("增强", "提高", "优化")
    dangerous_properties=("传播", "毒力", "感染能力")
    return(
        "病原体"in text
        and contains_any(text,enhancement_terms)
        and contains_any(text,dangerous_properties)
    )

def is_privacy_disclosure(text:str)->bool:
    """识别索取或传播可识别患者信息的请求。"""
    private_data_terms = (
        "患者姓名",
        "患者病历",
        "病历内容",
        "病历号",
    )
    disclosure_terms=(
        "发给我",
        "发送",
        "公开",
        "泄露",
        "不需要隐去",
        "无需脱敏",        
    )
    return contains_any(
        text,
        private_data_terms,
    ) and contains_any(text,disclosure_terms)

def is_dose_change(text:str)->bool:
    """识别要求直接改变药物剂量的表达。"""
    change_terms=(
        "加倍",
        "增加",
        "减少",
        "调整",
        "改变",
    )
    return "剂量" in text and contains_any(text,change_terms)


def check_request(task:str)->PolicyDecision:
    """在检索和模型调用前检查输入风险。"""
    text=task.strip().casefold()
    high_risk=(
        contains_any(text,HIGH_RISK_TERMS)
        or is_ethics_evasion(text)
        or is_pathogen_enhancement(text)
        or is_privacy_disclosure(text)
    )
    if high_risk:
        return PolicyDecision(
            allowed=False,
            reason=(
                "请求可能涉及病原体风险、人体研究、"
                "患者隐私或绕过监管。"
            ),
            next_action=(
                "拒绝具体实施指导，并建议联系有资质的"
                "机构或合规专业人员。"
            )
        )
        
    clinical_decision=(
        contains_any(text,CLINICAL_DECISION_TERMS)
        or is_dose_change(text)
    )


    if clinical_decision:
        return PolicyDecision(
            allowed=False,
            reason="请求要求个体化诊断、用药或治疗决策。",
            next_action=(
                "只能提供一般教育信息，并建议咨询"
                "合格医疗专业人员。"
            )
        )

    return PolicyDecision(
        allowed=True,
        reason="请求属于一般知识、研究方法或数据分析范围。",
        next_action="允许继续执行本地检索。",
    )

def check_model_output(text:str)->PolicyDecision:
    """在保存和返回前检查模型生成的文本。"""
    normalized = text.strip().casefold()

    if not normalized:
        return PolicyDecision(
            allowed=False,
            reason="模型返回了空内容。",
            next_action="不要保存空回答；检查模型接口或稍后重试。",
        )
    
    if contains_any(normalized,UNSAFE_MODEL_OUTPUT_TERMS):
        return PolicyDecision(
            allowed=False,
            reason=(
                "模型输出可能包含诊断、用药调整或"
                "高风险实施建议。"
            ),
            next_action=(
                "丢弃本次输出，不写入总结，并建议"
                "咨询合规专业人员。"
            )
        )
    

    return PolicyDecision(
        allowed=True,
        reason="模型输出未命中当前高风险规则。",
        next_action="允许执行长度限制和本地保存。",
    )