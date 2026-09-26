//! The daemon's exit contract (plan 2026-09-22-tvix-aios-step1, OS2, Interface 2).
//! Each test's doc comment names the one-line mutant that turns it red.

use std::process::{Command, Output};

fn run(args: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_aiosd"))
        .args(args)
        .output()
        .expect("aiosd runs")
}

fn fixture(name: &str) -> String {
    format!("{}/tests/fixtures/{name}", env!("CARGO_MANIFEST_DIR"))
}

/// Mutant: exit 0 and exit 2 swapped, or the summary printed to stderr.
#[test]
fn an_accepted_declaration_exits_0_with_the_summary_alone_on_stdout() {
    let out = run(&[&fixture("full.json")]);
    assert_eq!(out.status.code(), Some(0));
    assert_eq!(
        String::from_utf8(out.stdout).unwrap(),
        "aiosd: declaration ok version=1 vms=2 seats=3 workflows=1 worlds=1 egress=2 classes=2 guard-rules=2\n"
    );
    assert!(out.stderr.is_empty());
}

/// Mutant: the refusal printed to stdout, or a refused declaration exiting 1.
#[test]
fn a_refused_declaration_exits_2_with_the_reason_on_stderr_and_nothing_on_stdout() {
    for name in ["unknown-field.json", "syntax.json"] {
        let out = run(&[&fixture(name)]);
        assert_eq!(out.status.code(), Some(2), "{name}");
        assert!(out.stdout.is_empty(), "{name}");
        let err = String::from_utf8(out.stderr).unwrap();
        assert!(
            err.starts_with("aiosd: declaration refused: "),
            "{name}: {err}"
        );
    }
    let err = String::from_utf8(run(&[&fixture("unknown-field.json")]).stderr).unwrap();
    assert!(err.contains("colour"), "the unknown field is named: {err}");
}

/// Mutant: an unreadable path treated as a refusal (exit 2).
#[test]
fn an_unreadable_path_exits_1() {
    let out = run(&[&fixture("missing.json")]);
    assert_eq!(out.status.code(), Some(1));
    assert!(String::from_utf8(out.stderr)
        .unwrap()
        .starts_with("aiosd: cannot read "));
    assert!(out.stdout.is_empty());
}

/// Mutant: a missing or extra argument read as a path (exit 1) instead of usage.
#[test]
fn a_usage_error_exits_64() {
    let cases: [&[&str]; 2] = [&[], &["a", "b"]];
    for args in cases {
        let out = run(args);
        assert_eq!(out.status.code(), Some(64), "{args:?}");
        assert!(String::from_utf8(out.stderr)
            .unwrap()
            .contains("usage: aiosd <aios.json>"));
        assert!(out.stdout.is_empty());
    }
}
