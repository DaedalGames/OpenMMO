use std::io::ErrorKind;
use std::net::IpAddr;
use std::path::Path;
use tracing::warn;

/// Operator messages for one IP, one `IP message` per line with `#` comments.
/// Read on every send so edits apply without a restart; a missing file means
/// none. See doc/IP_NOTICES.md.
pub async fn notices_for(path: &Path, ip: IpAddr) -> Vec<String> {
    match tokio::fs::read_to_string(path).await {
        Ok(text) => parse(&text, ip),
        Err(e) if e.kind() == ErrorKind::NotFound => Vec::new(),
        Err(e) => {
            warn!("Cannot read IP notices from {}: {}", path.display(), e);
            Vec::new()
        }
    }
}

fn parse(text: &str, ip: IpAddr) -> Vec<String> {
    text.lines()
        .map(str::trim)
        .filter(|line| !line.is_empty() && !line.starts_with('#'))
        .filter_map(|line| {
            let (addr, message) = line.split_once(char::is_whitespace)?;
            let message = message.trim();
            (addr.parse::<IpAddr>().ok()? == ip && !message.is_empty()).then(|| message.to_string())
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    const FILE: &str = "\
# comment
220.89.217.201  첫 번째 안내
10.0.0.1 other
220.89.217.201\t두 번째 안내

not-an-ip message
220.89.217.201
";

    #[test]
    fn returns_every_message_for_the_ip_in_order() {
        let ip: IpAddr = "220.89.217.201".parse().unwrap();
        assert_eq!(parse(FILE, ip), vec!["첫 번째 안내", "두 번째 안내"]);
    }

    #[test]
    fn other_ips_get_nothing() {
        let ip: IpAddr = "220.89.217.202".parse().unwrap();
        assert!(parse(FILE, ip).is_empty());
    }

    #[tokio::test]
    async fn missing_file_means_no_notices() {
        let ip: IpAddr = "220.89.217.201".parse().unwrap();
        let path = Path::new("/nonexistent/ip_notices.txt");
        assert!(notices_for(path, ip).await.is_empty());
    }
}
