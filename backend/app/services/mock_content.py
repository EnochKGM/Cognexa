"""Mock study-material content.

This module contains handcrafted, realistic educational content used by
`MockStudyMaterialGenerator`.  It contains NO AI output.  The topic is chosen
deterministically from the upload id so the same image always yields the same
demo result (feels stable during a hackathon demo).

When the real `Gemma4StudyMaterialGenerator` is added, this module is simply
left behind — nothing else in the app depends on it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class ContentQuestion:
    question: str
    options: List[str]
    correct_answer: str
    explanation: str


@dataclass
class TopicContent:
    key: str
    label: str
    summary_overview: str
    summary_sections: List[dict]  # {"title", "content"}
    key_terms: List[dict]  # {"term", "definition"}
    subtopics: List[dict] = field(default_factory=list)  # {"label", "concepts": [str]}
    questions: List[ContentQuestion] = field(default_factory=list)


PHOTOSYNTHESIS = TopicContent(
    key="photosynthesis",
    label="Photosynthesis",
    summary_overview=(
        "Photosynthesis is the process by which plants, algae and some bacteria convert "
        "light energy into chemical energy stored in glucose. Using sunlight, water and "
        "carbon dioxide, these organisms build sugar molecules and release oxygen as a "
        "by-product — making photosynthesis the foundation of nearly every food chain on Earth."
    ),
    summary_sections=[
        {
            "title": "Where it happens",
            "content": (
                "Photosynthesis takes place in chloroplasts, organelles packed with the green "
                "pigment chlorophyll. Inside a chloroplast, thylakoid membranes host the "
                "light-dependent reactions, while the surrounding stroma hosts the Calvin cycle."
            ),
        },
        {
            "title": "The two stages",
            "content": (
                "The light reactions capture solar energy to split water (photolysis), producing "
                "oxygen, ATP and NADPH. The Calvin cycle then uses that ATP and NADPH to fix "
                "carbon dioxide into G3P, which the plant converts into glucose and other organic molecules."
            ),
        },
        {
            "title": "Overall equation",
            "content": (
                "6CO₂ + 6H₂O + light energy → C₆H₁₂O₆ + 6O₂. Reactants are carbon dioxide, water "
                "and light; products are glucose and oxygen."
            ),
        },
        {
            "title": "Why it matters",
            "content": (
                "Photosynthesis produces the oxygen we breathe and the organic matter that feeds "
                "ecosystems. It also removes carbon dioxide from the atmosphere, linking plant "
                "biology directly to the global carbon cycle and climate."
            ),
        },
    ],
    key_terms=[
        {"term": "Chlorophyll", "definition": "Green pigment that absorbs light energy, mainly red and blue wavelengths."},
        {"term": "Thylakoid", "definition": "Membrane sac inside chloroplasts where the light reactions occur."},
        {"term": "Stroma", "definition": "Fluid-filled space surrounding thylakoids; site of the Calvin cycle."},
        {"term": "RuBisCO", "definition": "Enzyme that fixes CO₂ into an organic molecule during the Calvin cycle."},
        {"term": "Photolysis", "definition": "Splitting of water using light, releasing oxygen, electrons and protons."},
        {"term": "NADPH", "definition": "Electron carrier produced in light reactions and used to build sugar."},
        {"term": "G3P", "definition": "Three-carbon sugar produced by the Calvin cycle; a glucose precursor."},
        {"term": "Chloroplast", "definition": "Organelle in plant and algal cells where photosynthesis happens."},
    ],
    subtopics=[
        {
            "label": "Light Reactions",
            "concepts": ["Photosystems I & II", "Water photolysis", "ATP & NADPH production"],
        },
        {
            "label": "Calvin Cycle",
            "concepts": ["Carbon fixation", "RuBisCO enzyme", "G3P sugar production"],
        },
        {
            "label": "Inputs & Outputs",
            "concepts": ["Sunlight", "Carbon dioxide", "Water", "Glucose & oxygen"],
        },
        {
            "label": "Factors Affecting Rate",
            "concepts": ["Light intensity", "CO₂ concentration", "Temperature"],
        },
        {
            "label": "Biological Importance",
            "concepts": ["Base of food chains", "Oxygen production", "Carbon cycle balance"],
        },
    ],
    questions=[
        ContentQuestion(
            question="Which organelle is the primary site of photosynthesis?",
            options=["Mitochondrion", "Chloroplast", "Ribosome", "Golgi apparatus"],
            correct_answer="Chloroplast",
            explanation=(
                "Chloroplasts contain chlorophyll and the thylakoid/stroma structures needed for "
                "both the light reactions and the Calvin cycle. Mitochondria perform cellular respiration."
            ),
        ),
        ContentQuestion(
            question="What are the main products of the light-dependent reactions?",
            options=[
                "Glucose and carbon dioxide",
                "ATP, NADPH and oxygen",
                "Water and sunlight",
                "RuBisCO and G3P",
            ],
            correct_answer="ATP, NADPH and oxygen",
            explanation=(
                "The light reactions convert solar energy into ATP and NADPH (used by the Calvin "
                "cycle) and split water, releasing oxygen as a by-product."
            ),
        ),
        ContentQuestion(
            question="Which enzyme is responsible for fixing carbon dioxide in the Calvin cycle?",
            options=["ATP synthase", "DNA polymerase", "RuBisCO", "Amylase"],
            correct_answer="RuBisCO",
            explanation=(
                "RuBisCO attaches CO₂ to RuBP, the first step of carbon fixation. It is considered "
                "the most abundant enzyme on Earth."
            ),
        ),
        ContentQuestion(
            question="Where does the oxygen released during photosynthesis come from?",
            options=["Carbon dioxide", "Glucose", "Water", "Chlorophyll"],
            correct_answer="Water",
            explanation=(
                "Isotope labelling experiments show the released O₂ comes from the splitting of "
                "water (photolysis) in the light reactions, not from CO₂."
            ),
        ),
        ContentQuestion(
            question="Which factor would MOST directly limit the rate of photosynthesis in bright light with ample water?",
            options=["CO₂ concentration", "Soil pH", "Moon phase", "Root depth"],
            correct_answer="CO₂ concentration",
            explanation=(
                "With light and water plentiful, carbon dioxide becomes the limiting factor: the "
                "Calvin cycle cannot run faster without more CO₂ for RuBisCO to fix."
            ),
        ),
    ],
)

WATER_CYCLE = TopicContent(
    key="water-cycle",
    label="The Water Cycle",
    summary_overview=(
        "The water cycle (hydrologic cycle) describes the continuous movement of water through "
        "Earth's systems: evaporating from oceans and land, condensing into clouds, falling as "
        "precipitation, and returning to the sea through runoff and groundwater. Driven by solar "
        "energy and gravity, it redistributes fresh water and shapes weather and climate."
    ),
    summary_sections=[
        {
            "title": "Evaporation & transpiration",
            "content": (
                "Heat from the sun turns liquid water from oceans, lakes and rivers into water "
                "vapour. Plants add to this moisture through transpiration, releasing vapour from "
                "their leaves. Together these processes move water into the atmosphere."
            ),
        },
        {
            "title": "Condensation & precipitation",
            "content": (
                "Rising vapour cools and condenses around tiny particles to form cloud droplets. "
                "When droplets combine and grow heavy enough, they fall as precipitation — rain, "
                "snow, sleet or hail depending on temperature."
            ),
        },
        {
            "title": "Collection & return flow",
            "content": (
                "Precipitated water collects in oceans, lakes and reservoirs, flows over land as "
                "runoff, or soaks into the ground as infiltration, replenishing groundwater that "
                "slowly migrates back to the sea or feeds springs and wells."
            ),
        },
        {
            "title": "A closed system",
            "content": (
                "Earth's water is finite: the same water recycles endlessly, changing state and "
                "location but never being created or destroyed — conservation of mass drives the "
                "entire cycle."
            ),
        },
    ],
    key_terms=[
        {"term": "Evaporation", "definition": "Change of liquid water into water vapour driven by heat."},
        {"term": "Transpiration", "definition": "Release of water vapour from plant leaves into the atmosphere."},
        {"term": "Condensation", "definition": "Cooling of vapour into liquid droplets that form clouds and fog."},
        {"term": "Precipitation", "definition": "Water falling from clouds as rain, snow, sleet or hail."},
        {"term": "Infiltration", "definition": "Soaking of water into soil and rock, recharging groundwater."},
        {"term": "Runoff", "definition": "Surface flow of water over land toward streams, rivers and oceans."},
        {"term": "Groundwater", "definition": "Water stored in underground soil and rock pores."},
        {"term": "Collection", "definition": "Accumulation of water in oceans, lakes, reservoirs and ice."},
    ],
    subtopics=[
        {
            "label": "Evaporation & Transpiration",
            "concepts": ["Solar-driven evaporation", "Plant transpiration"],
        },
        {
            "label": "Condensation",
            "concepts": ["Cloud formation", "Water vapour cooling"],
        },
        {
            "label": "Precipitation",
            "concepts": ["Rain, snow, sleet, hail", "Saturated air"],
        },
        {
            "label": "Collection & Runoff",
            "concepts": ["Oceans & lakes", "River systems"],
        },
        {
            "label": "Infiltration & Groundwater",
            "concepts": ["Soil absorption", "Aquifers"],
        },
    ],
    questions=[
        ContentQuestion(
            question="What is the primary energy source that drives the water cycle?",
            options=["The moon", "The sun", "Earth's core", "Ocean currents"],
            correct_answer="The sun",
            explanation=(
                "Solar energy powers evaporation and transpiration, lifting water into the "
                "atmosphere; gravity then returns it as precipitation and runoff."
            ),
        ),
        ContentQuestion(
            question="Which process releases water vapour from plant leaves?",
            options=["Respiration", "Transpiration", "Condensation", "Infiltration"],
            correct_answer="Transpiration",
            explanation=(
                "Transpiration is evaporation from leaf stomata. Together with evaporation from "
                "water bodies it is called evapotranspiration."
            ),
        ),
        ContentQuestion(
            question="Clouds form when water vapour undergoes:",
            options=["Evaporation", "Condensation", "Sublimation", "Runoff"],
            correct_answer="Condensation",
            explanation=(
                "Rising vapour cools and condenses onto tiny particles, forming the droplets or "
                "ice crystals that make up clouds."
            ),
        ),
        ContentQuestion(
            question="Water that soaks into soil and recharges aquifers is moving by:",
            options=["Runoff", "Infiltration", "Evaporation", "Transpiration"],
            correct_answer="Infiltration",
            explanation=(
                "Infiltration carries water below the surface where it becomes groundwater, "
                "stored in aquifers and released slowly to springs and rivers."
            ),
        ),
        ContentQuestion(
            question="Earth's total water supply is best described as:",
            options=[
                "Constantly created by rain",
                "A finite amount that recycles endlessly",
                "Slowly shrinking each year",
                "Replenished by comets",
            ],
            correct_answer="A finite amount that recycles endlessly",
            explanation=(
                "The water cycle is closed: the same water changes state and location but the "
                "total mass on Earth stays essentially constant."
            ),
        ),
    ],
)

TOPICS: List[TopicContent] = [PHOTOSYNTHESIS, WATER_CYCLE]
