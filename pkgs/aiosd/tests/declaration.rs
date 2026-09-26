//! The declaration module, black-box (plan 2026-09-22-tvix-aios-step1, OS2).
//! Each test's doc comment names the one-line mutant that turns it red.

use aiosd::declaration::{Declaration, Error, Harness, Placement, RuleKind, Unit};
use serde_json::{json, Value};

const EMPTY: &str = include_str!("fixtures/empty.json");
const FULL: &str = include_str!("fixtures/full.json");

/// The six name-keyed maps of the schema: an entry added to or removed from
/// one of them is a different declaration, not a shape violation, so the
/// walks below skip them.
const MAPS: &[&str] = &[
    "/vms",
    "/seats",
    "/workflows",
    "/worlds",
    "/egress",
    "/policy/classes",
];

fn parse(text: &str) -> Result<Declaration, Error> {
    Declaration::parse(text.as_bytes())
}

fn root() -> Value {
    serde_json::from_str(FULL).expect("full.json is JSON")
}

/// Every JSON pointer at which `v` holds an object, depth first, `at` first.
fn object_pointers(v: &Value, at: &str, out: &mut Vec<String>) {
    match v {
        Value::Object(map) => {
            out.push(at.to_string());
            for (k, child) in map {
                object_pointers(child, &format!("{at}/{k}"), out);
            }
        }
        Value::Array(items) => {
            for (i, child) in items.iter().enumerate() {
                object_pointers(child, &format!("{at}/{i}"), out);
            }
        }
        _ => {}
    }
}

/// `full.json` with the value at `pointer` replaced.
fn with(pointer: &str, value: Value) -> String {
    let mut v = root();
    *v.pointer_mut(pointer).expect("pointer exists") = value;
    serde_json::to_string(&v).unwrap()
}

/// Mutant: `rename_all = "kebab-case"` on `Harness` changed, an arm renamed,
/// `Placement`'s tag spelling changed, or two of `summary()`'s counts crossed.
#[test]
fn the_full_declaration_parses_with_every_arm() {
    let d = parse(FULL).expect("full.json parses");
    assert_eq!(d.seats["claude"].harness, Harness::ClaudeCode);
    assert_eq!(d.seats["dsh"].harness, Harness::Dsh);
    assert_eq!(d.seats["codex"].harness, Harness::Codex);
    assert_eq!(d.seats["claude"].placement, Placement::Vm("guest-a".into()));
    assert_eq!(d.seats["dsh"].placement, Placement::Unit(Unit::default()));
    assert_eq!(d.worlds["sfw"].placement, Placement::Unit(Unit::default()));
    assert_eq!(d.policy.guard[0].kind, RuleKind::File);
    assert_eq!(d.policy.guard[1].kind, RuleKind::Dir);
    assert_eq!(d.vms["guest-a"].shares[0].mount_point, "/workspace");
    assert_eq!(d.egress["seat"].listen_port, 3128);
    assert_eq!(d.worlds["sfw"].loop_.rounds, 1);
    assert_eq!(
        d.summary(),
        "aiosd: declaration ok version=1 vms=2 seats=3 workflows=1 worlds=1 egress=2 classes=2 guard-rules=2"
    );
}

/// Mutant: `summary()` prints a constant, or a count reads the wrong map.
#[test]
fn the_empty_declaration_counts_zero() {
    assert_eq!(
        parse(EMPTY).expect("empty.json parses").summary(),
        "aiosd: declaration ok version=1 vms=0 seats=0 workflows=0 worlds=0 egress=0 classes=0 guard-rules=0"
    );
}

/// Mutant: `#[serde(deny_unknown_fields)]` dropped from any one struct — the
/// walk plants a field in every object of the fixture, so each struct is tried.
#[test]
fn an_unknown_field_in_any_object_is_refused() {
    let root = root();
    let mut pointers = Vec::new();
    object_pointers(&root, "", &mut pointers);
    assert!(
        pointers.len() >= 25,
        "{} objects in the fixture",
        pointers.len()
    );
    for p in &pointers {
        let mut v = root.clone();
        v.pointer_mut(p)
            .unwrap()
            .as_object_mut()
            .unwrap()
            .insert("unexpected".into(), Value::Bool(true));
        let text = serde_json::to_string(&v).unwrap();
        assert!(
            parse(&text).is_err(),
            "an unknown field at {p:?} was accepted"
        );
    }
}

/// Mutant: `#[serde(default)]` (or an `Option`) on any one field — the walk
/// deletes every key of every struct-shaped object, so each field is tried.
#[test]
fn a_missing_field_in_any_object_is_refused() {
    let root = root();
    let mut pointers = Vec::new();
    object_pointers(&root, "", &mut pointers);
    let mut tried = 0;
    for p in &pointers {
        if MAPS.contains(&p.as_str()) {
            continue;
        }
        let keys: Vec<String> = root
            .pointer(p)
            .unwrap()
            .as_object()
            .unwrap()
            .keys()
            .cloned()
            .collect();
        for k in keys {
            let mut v = root.clone();
            v.pointer_mut(p)
                .unwrap()
                .as_object_mut()
                .unwrap()
                .remove(&k);
            let text = serde_json::to_string(&v).unwrap();
            assert!(
                parse(&text).is_err(),
                "a missing {k:?} at {p:?} was accepted"
            );
            tried += 1;
        }
    }
    assert!(tried >= 50, "{tried} fields tried");
}

/// Mutant: a catch-all `#[serde(other)]` arm on `Harness`, `Placement` or `RuleKind`.
#[test]
fn an_unknown_arm_is_refused() {
    for (pointer, bad) in [
        ("/seats/dsh/harness", json!("hermes")),
        ("/seats/dsh/placement", json!({ "pod": {} })),
        ("/policy/guard/0/kind", json!("symlink")),
    ] {
        assert!(
            parse(&with(pointer, bad)).is_err(),
            "{pointer} accepted an unknown arm"
        );
    }
}

/// Mutant: the `validate()` call dropped from `parse()`, or the store-dir
/// prefix check replaced by `starts_with("/")`.
#[test]
fn a_vm_config_that_is_not_a_store_path_is_refused() {
    let outside = parse(&with("/vms/guest-a/config", json!("/etc/passwd"))).unwrap_err();
    assert!(
        matches!(outside, Error::NotAStorePath { ref vm, .. } if vm == "guest-a"),
        "{outside}"
    );
    assert!(outside.to_string().contains("store"), "{outside}");
    let bad_digest =
        parse(&with("/vms/guest-a/config", json!("/nix/store/zzz-guest"))).unwrap_err();
    assert!(
        matches!(bad_digest, Error::NotAStorePath { .. }),
        "{bad_digest}"
    );
}

/// Mutant: `!= VERSION` weakened to `< VERSION`.
#[test]
fn a_version_other_than_1_is_refused() {
    let e = parse(&with("/version", json!(2))).unwrap_err();
    assert!(matches!(e, Error::Version(2)), "{e}");
    assert_eq!(e.to_string(), "version 2 is not 1");
}
