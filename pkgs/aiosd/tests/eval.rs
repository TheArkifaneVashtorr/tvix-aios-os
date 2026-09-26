//! The second fork crate: tvix-eval renders a declaration that the parser
//! accepts (spec 2026-09-22-tvix-aios §5: evaluating the declaration in tests
//! without a Nix daemon). Mutant: `tvix-eval` removed from [dev-dependencies]
//! — this file no longer compiles; `version = 1` changed in `code` — the
//! parser refuses it.

use aiosd::declaration::Declaration;
use tvix_eval::Evaluation;

#[test]
fn a_declaration_rendered_by_tvix_eval_parses() {
    let code = "builtins.toJSON { version = 1; vms = {}; seats = {}; workflows = {}; worlds = {}; egress = {}; policy = { guard = []; classes = {}; }; }";
    let result = Evaluation::builder_pure().build().evaluate(code, None);
    assert!(result.errors.is_empty(), "{:?}", result.errors);
    let value = result.value.expect("the evaluation produced a value");
    let json = value.to_str().expect("toJSON yields a context-less string");
    let decl = Declaration::parse(json.as_bytes()).expect("the rendered declaration parses");
    assert_eq!(
        decl.summary(),
        "aiosd: declaration ok version=1 vms=0 seats=0 workflows=0 worlds=0 egress=0 classes=0 guard-rules=0"
    );
}
