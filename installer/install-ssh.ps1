#Requires -RunAsAdministrator

$sshCapability = Get-WindowsCapability -Online | Where-Object Name -like 'OpenSSH.Server*'

if ($sshCapability.State -eq 'NotPresent') {
    Add-WindowsCapability -Online -Name $sshCapability.Name
} 

Set-Service -Name sshd -StartupType 'Automatic'

$firewallRuleName = "OpenSSH-Server-In-TCP"
if (-not (Get-NetFirewallRule -Name $firewallRuleName -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -Name $firewallRuleName -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
}

Start-Service sshd
