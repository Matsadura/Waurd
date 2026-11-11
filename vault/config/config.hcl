ui = true                  # Enables the Vault web interface.

disable_mlock = true       #Allows sensitive memory pages to be swapped to disk

listener "tcp" {           # Configures Vault's TCP network listener.
  address     = "0.0.0.0:8200" # Listens on port 8200 on all network interfaces.
  tls_disable = true       # Disables TLS (HTTP only; local development).
}

storage "file" {           # Uses filesystem storage to persist Vault data.
  path = "/vault/data"     # Directory where Vault stores its data.
}
