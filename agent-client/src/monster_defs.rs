use serde::Deserialize;
use std::collections::HashMap;
use std::sync::LazyLock;

#[derive(Deserialize)]
struct MonsterDef {
    name: String,
}

static DEFS: LazyLock<HashMap<String, MonsterDef>> = LazyLock::new(|| {
    serde_json::from_str(include_str!("../../data/monsters.json"))
        .expect("invalid embedded monster definitions")
});

static MONSTER_TERMS: LazyLock<Vec<String>> = LazyLock::new(|| {
    let mut terms = Vec::new();
    for (id, def) in DEFS
        .iter()
        .filter(|(id, _)| !matches!(id.as_str(), "terraclash" | "barkan"))
    {
        for term in [id, &def.name] {
            let term = term.to_lowercase();
            terms.push(format!("{term}s"));
            terms.push(term);
        }
    }
    terms.sort_unstable();
    terms.dedup();
    terms
});

pub fn monster_name(id: &str) -> &str {
    DEFS.get(id).map_or(id, |def| def.name.as_str())
}

pub fn is_combat_report(text: &str) -> bool {
    let text = text.to_lowercase();
    let word = |term: &str| {
        text.match_indices(term).any(|(i, _)| {
            let boundary = |c: char| !c.is_ascii_alphanumeric() && c != '_';
            text[..i].chars().next_back().is_none_or(boundary)
                && text[i + term.len()..].chars().next().is_none_or(boundary)
        })
    };
    [
        "monster",
        "monsters",
        "beast",
        "beasts",
        "warned",
        "retreated",
        "withdrew",
        "attacker",
        "attackers",
        "killed",
    ]
    .iter()
    .any(|term| word(term))
        || ["조심", "경고", "배회", "후퇴", "몬스터"]
            .iter()
            .any(|term| text.contains(term))
        || MONSTER_TERMS.iter().any(|term| word(term))
}

#[cfg(test)]
mod tests {
    #[test]
    fn combat_reports_are_distinct_from_research_and_social_memories() {
        for text in [
            "A gnoll is near camp",
            "Gnoll이 남동쪽에 있어",
            "jake5 killed the hobgoblin",
            "Warned jake5 about the remaining beasts",
            "Several gnolls appeared",
        ] {
            assert!(super::is_combat_report(text), "{text}");
        }
        for text in [
            "Terraclash once protected this land",
            "Barkan sealed the heart's force into amulets",
            "jake5 prefers Korean",
            "테라클래시와 바르칸의 역사를 연구한다",
        ] {
            assert!(!super::is_combat_report(text), "{text}");
        }
    }
}
