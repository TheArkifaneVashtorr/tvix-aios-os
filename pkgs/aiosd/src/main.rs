//! aiosd, step 1: read the declaration named on the command line, print one
//! summary line or the refusal, and exit. Exit 0: accepted (the summary on
//! stdout, nothing on stderr). Exit 1: the file cannot be read. Exit 2: the
//! declaration is refused (`aiosd: declaration refused: <why>` on stderr,
//! nothing on stdout). Exit 64: usage (`usage: aiosd <aios.json>` on stderr).
#![forbid(unsafe_code)]

use std::process::ExitCode;

use aiosd::declaration::Declaration;

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 2 {
        eprintln!("usage: aiosd <aios.json>");
        return ExitCode::from(64);
    }
    let path = &args[1];
    let bytes = match std::fs::read(path) {
        Ok(bytes) => bytes,
        Err(e) => {
            eprintln!("aiosd: cannot read {path}: {e}");
            return ExitCode::from(1);
        }
    };
    match Declaration::parse(&bytes) {
        Ok(decl) => {
            println!("{}", decl.summary());
            ExitCode::SUCCESS
        }
        Err(e) => {
            eprintln!("aiosd: declaration refused: {e}");
            ExitCode::from(2)
        }
    }
}
