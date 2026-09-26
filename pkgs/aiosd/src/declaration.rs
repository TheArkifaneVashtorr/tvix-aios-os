//! The declaration: `aios.json`, the store-path rendering of `options.aios`
//! (spec 2026-09-22-tvix-aios §4), parsed with serde into typed views.
//!
//! Shape is enforced here — every field required, every enum arm named, an
//! unknown field anywhere refused, a VM's `config` a well-formed store path
//! (nix-compat's parser). The referential rules of §4 (a seat's `egress`
//! names a declared instance, a `placement.vm` names a declared VM with the
//! same egress) are the NixOS module's evaluation-time assertions of a later
//! step and are not re-implemented here.

use std::collections::BTreeMap;
use std::fmt;

use nix_compat::store_path::StorePath;
use serde::Deserialize;

/// The one declaration version this daemon reads.
pub const VERSION: u32 = 1;

#[derive(Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Declaration {
    pub version: u32,
    pub vms: BTreeMap<String, Vm>,
    pub seats: BTreeMap<String, Seat>,
    pub workflows: BTreeMap<String, Workflow>,
    pub worlds: BTreeMap<String, World>,
    pub egress: BTreeMap<String, Egress>,
    pub policy: Policy,
}

#[derive(Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Vm {
    /// The guest's NixOS toplevel: an absolute store path.
    pub config: String,
    pub shares: Vec<Share>,
    pub vsock: Vsock,
    pub baskets: Vec<String>,
    /// The name of an `egress` entry.
    pub egress: String,
}

#[derive(Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Share {
    pub source: String,
    #[serde(rename = "mountPoint")]
    pub mount_point: String,
}

#[derive(Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Vsock {
    pub cid: u32,
}

#[derive(Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Seat {
    pub harness: Harness,
    pub role: String,
    pub baskets: Vec<String>,
    pub egress: String,
    pub placement: Placement,
}

#[derive(Debug, Deserialize, PartialEq, Eq, Clone, Copy)]
#[serde(rename_all = "kebab-case")]
pub enum Harness {
    ClaudeCode,
    Dsh,
    Codex,
}

/// `{"vm": "<name>"}` or `{"unit": {}}` — nothing else.
#[derive(Debug, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum Placement {
    Vm(String),
    Unit(Unit),
}

#[derive(Debug, Deserialize, PartialEq, Eq, Default)]
#[serde(deny_unknown_fields)]
pub struct Unit {}

#[derive(Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Workflow {
    pub source: WorkflowSource,
    /// A routing role (docs/ledger/routing.toml).
    pub ladder: String,
    pub gates: Vec<String>,
    pub cap: u32,
}

#[derive(Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct WorkflowSource {
    pub plan: String,
    pub keys: Vec<String>,
}

#[derive(Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct World {
    pub generator: String,
    #[serde(rename = "loop")]
    pub loop_: Loop,
    /// An evidence kind (pkgs/evidence/streams.py KINDS).
    pub sink: String,
    pub placement: Placement,
}

#[derive(Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Loop {
    pub rounds: u32,
    pub judge: String,
}

#[derive(Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Egress {
    #[serde(rename = "listenPort")]
    pub listen_port: u16,
    pub allow: Vec<String>,
}

#[derive(Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Policy {
    /// services.orchestrator-guard.rules (IS23), in declaration order.
    pub guard: Vec<GuardRule>,
    /// services.baskets.definitions.
    pub classes: BTreeMap<String, Class>,
}

#[derive(Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct GuardRule {
    pub path: String,
    pub kind: RuleKind,
    pub reason: String,
}

#[derive(Debug, Deserialize, PartialEq, Eq, Clone, Copy)]
#[serde(rename_all = "lowercase")]
pub enum RuleKind {
    Dir,
    File,
}

#[derive(Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Class {
    pub classification: String,
    pub mount: String,
}

/// Why a declaration was refused. `Display` is the one line the daemon prints.
#[derive(Debug)]
pub enum Error {
    /// Not JSON, not the shape above, or an unknown field (serde's message names it).
    Json(serde_json::Error),
    /// A `version` other than [`VERSION`].
    Version(u32),
    /// A VM's `config` that nix-compat does not parse as an absolute store path.
    NotAStorePath {
        vm: String,
        value: String,
        reason: nix_compat::store_path::Error,
    },
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Error::Json(e) => write!(f, "{e}"),
            Error::Version(v) => write!(f, "version {v} is not {VERSION}"),
            Error::NotAStorePath { vm, value, reason } => {
                write!(f, "vms.{vm}.config {value:?} is not a store path: {reason}")
            }
        }
    }
}

impl std::error::Error for Error {}

impl Declaration {
    /// Parse the bytes of `aios.json`: the shape, then the rules the shape
    /// cannot express. Nothing is read from anywhere else.
    pub fn parse(bytes: &[u8]) -> Result<Self, Error> {
        let decl: Declaration = serde_json::from_slice(bytes).map_err(Error::Json)?;
        decl.validate()?;
        Ok(decl)
    }

    fn validate(&self) -> Result<(), Error> {
        if self.version != VERSION {
            return Err(Error::Version(self.version));
        }
        for (name, vm) in &self.vms {
            StorePath::<String>::from_absolute_path(vm.config.as_bytes()).map_err(|reason| {
                Error::NotAStorePath {
                    vm: name.clone(),
                    value: vm.config.clone(),
                    reason,
                }
            })?;
        }
        Ok(())
    }

    /// The one line the daemon prints for an accepted declaration.
    pub fn summary(&self) -> String {
        format!(
            "aiosd: declaration ok version={} vms={} seats={} workflows={} worlds={} egress={} classes={} guard-rules={}",
            self.version,
            self.vms.len(),
            self.seats.len(),
            self.workflows.len(),
            self.worlds.len(),
            self.egress.len(),
            self.policy.classes.len(),
            self.policy.guard.len()
        )
    }
}
