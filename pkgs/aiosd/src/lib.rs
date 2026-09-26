//! aiosd — the tvix-aios daemon. Step 1 (plan 2026-09-22-tvix-aios-step1, OS2)
//! is the `declaration` module alone: the rendered `aios.json` parsed into
//! typed views and refused on any unknown field; the daemon starts from
//! nothing else.
#![forbid(unsafe_code)]

pub mod declaration;
