# secret/waurd/database is an address inside Vault storage (the server not the container)
path "secret/data/waurd/database" {
  capabilities = ["read"]
}
