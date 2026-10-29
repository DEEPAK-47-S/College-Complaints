"""
AUGIS Gemini AI Intelligence Service
Integrates Google Gemini AI (Google AI Studio) via the official google-genai SDK
for deep regulatory semantic analysis, cross-bureau conflict detection,
and AI-assisted grievance overlap explanation.
"""

import os
import json
import logging
from django.conf import settings

logger = logging.getLogger('augis.intelligence')

class GeminiAnalysisService:
    @staticmethod
    def is_gemini_configured():
        """Returns True if a valid Gemini API key is configured."""
        api_key = getattr(settings, 'GEMINI_API_KEY', '') or os.environ.get('GEMINI_API_KEY', '')
        return bool(api_key and api_key.strip() and not api_key.startswith('your_'))

    @classmethod
    def analyze_overlap(cls, candidate, force_refresh=False):
        """
        Analyzes a pair of complaints in an OverlapCandidate using Google Gemini AI.
        Returns a structured dictionary with regulatory insights.
        """
        if candidate.gemini_analysis and not force_refresh:
            return candidate.gemini_analysis

        first = candidate.first_complaint
        second = candidate.second_complaint
        inst = first.institution

        api_key = getattr(settings, 'GEMINI_API_KEY', '') or os.environ.get('GEMINI_API_KEY', '')
        model_name = getattr(settings, 'GEMINI_MODEL', 'gemini-2.5-flash')

        # Check if live Gemini API is configured
        if cls.is_gemini_configured():
            try:
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=api_key)

                prompt = f"""
You are the Chief Regulatory Grievance Intelligence Analyst for the All India Council for Technical Education (AICTE).
Analyze these two complaint cases registered against the same technical institution across AICTE Bureaus/Cells.

INSTITUTION PARTICULARS:
- Name: {inst.name}
- AICTE Permanent ID: {inst.aicte_permanent_id}
- Location: {inst.district}, {inst.state} (Region: {inst.get_region_display()})

COMPLAINT CASE 1:
- Case ID: {first.complaint_no}
- Handling Bureau: {first.currently_assigned_bureau.name} ({first.currently_assigned_bureau.code})
- Grievance Category: {first.category.name}
- Status: {first.get_current_status_display()}
- Title: {first.title}
- Complainant Allegations:
\"\"\"{first.description}\"\"\"

COMPLAINT CASE 2:
- Case ID: {second.complaint_no}
- Handling Bureau: {second.currently_assigned_bureau.name} ({second.currently_assigned_bureau.code})
- Grievance Category: {second.category.name}
- Status: {second.get_current_status_display()}
- Title: {second.title}
- Complainant Allegations:
\"\"\"{second.description}\"\"\"

TASK:
Evaluate whether these cases represent:
1. "POTENTIAL_OVERLAPPING_CASES" (Same factual matter or related violation requiring inter-bureau coordination)
2. "DUPLICATE_ALLEGATIONS" (Identical complainant allegation received through multiple channels)
3. "SEPARATE_INDEPENDENT_ISSUES" (Distinct operational matters concerning the same institution)

Determine:
- Overlap Confidence Index (0 to 100%)
- Regulatory Conflict Risk (HIGH, MEDIUM, or LOW: risk of parallel or conflicting orders by different Bureaus)
- Executive Justification (2-3 clear sentences explaining why they are related or distinct)
- Recommended Lead Bureau (Which bureau should take charge: {first.currently_assigned_bureau.code} or {second.currently_assigned_bureau.code}?)
- Recommended Coordination Actions (Array of 3 actionable steps for the handling officers)

Respond ONLY with a valid JSON object matching this schema:
{{
  "overlap_score_percent": int,
  "conflict_risk": "HIGH" | "MEDIUM" | "LOW",
  "conflict_reason": "string",
  "classification": "POTENTIAL_OVERLAPPING_CASES" | "DUPLICATE_ALLEGATIONS" | "SEPARATE_INDEPENDENT_ISSUES",
  "executive_summary": "string",
  "recommended_lead_bureau": "string",
  "coordination_steps": ["step1", "step2", "step3"],
  "model_used": "{model_name}"
}}
"""
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.2,
                        response_mime_type="application/json"
                    )
                )

                parsed_json = json.loads(response.text)
                parsed_json["is_live_gemini"] = True
                parsed_json["engine"] = f"Google Gemini ({model_name})"

                candidate.gemini_analysis = parsed_json
                candidate.model_version = f"gemini-{model_name}-hybrid"
                candidate.save(update_fields=['gemini_analysis', 'model_version'])
                return parsed_json

            except Exception as e:
                logger.error(f"Gemini API invocation failed: {e}. Falling back to rule-based synthesis.")

        # Fallback Synthesis (when GEMINI_API_KEY is not set or API error)
        is_cross = first.currently_assigned_bureau_id != second.currently_assigned_bureau_id
        is_same_cat = first.category_id == second.category_id
        score_pct = int(round(candidate.combined_score * 100))

        if is_cross and candidate.combined_score >= 0.5:
            classification = "POTENTIAL_OVERLAPPING_CASES"
            conflict_risk = "HIGH"
            lead_bureau = "RB" if "RB" in [first.currently_assigned_bureau.code, second.currently_assigned_bureau.code] else first.currently_assigned_bureau.code
            conflict_reason = f"Simultaneous active inquiry by {first.currently_assigned_bureau.code} and {second.currently_assigned_bureau.code} creates risk of divergent regulatory findings."
            exec_summary = f"Multiple AICTE Bureaus are actively investigating {inst.name}. Allegations share substantive factual alignment in grievance domain ({first.category.name}). Coordinated posture required to prevent duplicate hearings."
        elif candidate.combined_score >= 0.7:
            classification = "DUPLICATE_ALLEGATIONS"
            conflict_risk = "MEDIUM"
            lead_bureau = first.currently_assigned_bureau.code
            conflict_reason = "Substantial textual and semantic duplication observed in grievance narrative."
            exec_summary = f"Grievance narratives against {inst.name} indicate redundant complaint lodgment across administrative channels."
        else:
            classification = "SEPARATE_INDEPENDENT_ISSUES"
            conflict_risk = "LOW"
            lead_bureau = first.currently_assigned_bureau.code
            conflict_reason = "Complaints address distinct operational or academic dimensions despite sharing the same institution."
            exec_summary = f"Both grievances concern {inst.name} but address separate regulatory facets with isolated evidentiary requirements."

        simulated_analysis = {
            "overlap_score_percent": score_pct,
            "conflict_risk": conflict_risk,
            "conflict_reason": conflict_reason,
            "classification": classification,
            "executive_summary": exec_summary,
            "recommended_lead_bureau": lead_bureau,
            "coordination_steps": [
                f"Designate {lead_bureau} as the Coordinating Bureau to maintain primary case docket.",
                "Share verified evidentiary documents via Cross-Bureau Coordination Workspace.",
                "Issue joint show-cause inquiry notice to prevent contradictory institutional hearings."
            ],
            "model_used": "Local Semantic Hybrid (TF-IDF + MiniLM)",
            "is_live_gemini": False,
            "note": "Configure GEMINI_API_KEY in .env to enable real-time Google Gemini AI inference."
        }

        candidate.gemini_analysis = simulated_analysis
        candidate.save(update_fields=['gemini_analysis'])
        return simulated_analysis
