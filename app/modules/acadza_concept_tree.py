import json
from difflib import get_close_matches

file_location = file_location = "app/modules/acadza_concept_tree.json"
def load_concept_tree():
    with open(file_location, "r", encoding="utf-8") as f:
        return json.load(f)


#def fuzzy_match_context(tree, subjects, chapters, concepts, raw_query=None, detected_groups=None):
"""   matched = {}

    if detected_groups:  # ✅ Segment-aware mode if detected_groups exists
        for group in detected_groups:
            dost_type = group.get("dost_type")
            group_chapters = group.get("chapters", [])
            group_concepts = group.get("concepts", [])

            for chap in group_chapters:
                for stream in tree:
                    for subject in tree[stream]:
                        chap_match = get_close_matches(chap, tree[stream][subject].keys(), n=1, cutoff=0.6)
                        if chap_match:
                            chapter = chap_match[0]
                            matched.setdefault(subject, {})
                            matched[subject].setdefault(chapter, {"concepts": [], "subconcepts": {}})

                            if not group_concepts:
                                # ✅ If no concept explicitly mentioned, use all concepts
                                all_concepts = list(tree[stream][subject][chapter].keys())
                                matched[subject][chapter]["concepts"] = all_concepts
                                for concept in all_concepts:
                                    matched[subject][chapter]["subconcepts"][concept] = tree[stream][subject][chapter][concept]
                            else:
                                for con in group_concepts:
                                    concept_match = get_close_matches(con, tree[stream][subject][chapter].keys(), n=1, cutoff=0.6)
                                    if concept_match:
                                        concept = concept_match[0]
                                        matched[subject][chapter]["concepts"].append(concept)
                                        matched[subject][chapter]["subconcepts"][concept] = tree[stream][subject][chapter][concept]

    else:  # ✅ Legacy fallback mode
        for chap in chapters:
            for stream in tree:
                for subject in tree[stream]:
                    chap_match = get_close_matches(chap, tree[stream][subject].keys(), n=1, cutoff=0.6)
                    if chap_match:
                        chapter = chap_match[0]
                        matched.setdefault(subject, {})
                        matched[subject].setdefault(chapter, {"concepts": [], "subconcepts": {}})

                        if not concepts:
                            # ✅ If no concept explicitly mentioned, use all concepts
                            all_concepts = list(tree[stream][subject][chapter].keys())
                            matched[subject][chapter]["concepts"] = all_concepts
                            for concept in all_concepts:
                                matched[subject][chapter]["subconcepts"][concept] = tree[stream][subject][chapter][concept]
                        else:
                            for con in concepts:
                                concept_match = get_close_matches(con, tree[stream][subject][chapter].keys(), n=1, cutoff=0.6)
                                if concept_match:
                                    concept = concept_match[0]
                                    matched[subject][chapter]["concepts"].append(concept)
                                    matched[subject][chapter]["subconcepts"][concept] = tree[stream][subject][chapter][concept]

    # Subconcept reverse match if everything else fails
    if not matched and raw_query:
        raw_lower = raw_query.lower()
        for stream in tree:
            for subject in tree[stream]:
                for chapter in tree[stream][subject]:
                    for concept in tree[stream][subject][chapter]:
                        for subcon in tree[stream][subject][chapter][concept]:
                            if subcon.lower() in raw_lower:
                                matched[subject] = {
                                    chapter: {
                                        "concepts": [concept],
                                        "subconcepts": {concept: [subcon]}
                                    }
                                }
                                return matched

    return matched
    """