"""
 _                _     __  _____ _____              _   
| |              | |   /  ||  _  |  _  |            | |  
| |__   __ _  ___| | __`| || |/' |\ V /   _ __   ___| |_ 
| '_ \ / _` |/ __| |/ / | ||  /| |/ _ \  | '_ \ / _ \ __|
| | | | (_| | (__|   < _| |\ |_/ / |_| |_| | | |  __/ |_ 
|_| |_|\__,_|\___|_|\_\\___/\___/\_____(_)_| |_|\___|\__|
                                                         
Simple tool to retrieve IMAP accounts and save it to EML files

Error Handling for Connection:
-> Handles issues like incorrect server address, port, or network problems with clear messages.

Authentication Errors:
-> Detects invalid username or password and informs the user.

Mailbox Errors:
-> Skips inaccessible or unreadable mailboxes without halting the script.
-> Gracefully handles cases where mailboxes are empty or messages can't be retrieved.

Secure Password Input:
-> Uses getpass to securely hide the password when typing.

"""

import imaplib
import os
import email
from email import policy
from getpass import getpass

def get_user_inputs():
    """Prompts the user for server, port, username, and password."""
    server = input("Enter IMAP server: ").strip()
    port = input("Enter IMAP port (default 993): ").strip() or "993"
    username = input("Enter your email address: ").strip()
    password = getpass("Enter your password: ").strip()  # Hides password input
    return server, port, username, password

def connect_to_imap(server, port, username, password):
    """Connects to the IMAP server and logs in."""
    try:
        mail = imaplib.IMAP4_SSL(server, int(port))
    except imaplib.IMAP4.error:
        print(f"Error: Could not connect to {server}:{port}. Check the server and port.")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

    try:
        mail.login(username, password)
        print("Connected to IMAP server and logged in successfully.")
        return mail
    except imaplib.IMAP4.error:
        print("Error: Login failed. Check your username and password.")
        return None
    except Exception as e:
        print(f"Unexpected error during login: {e}")
        return None

def list_mailboxes(mail):
    """Lists all mailboxes in the account."""
    try:
        status, mailboxes = mail.list()
        if status == "OK":
            return [box.split()[-1].decode() for box in mailboxes]
        else:
            print("Error: Failed to retrieve mailboxes.")
            return []
    except Exception as e:
        print(f"Error listing mailboxes: {e}")
        return []

def download_emails(mail, mailbox, output_dir):
    """Downloads all emails from a specified mailbox and saves them as .eml files."""
    try:
        status, _ = mail.select(mailbox)
        if status != "OK":
            print(f"Error: Could not select mailbox {mailbox}. Skipping.")
            return

        status, messages = mail.search(None, "ALL")
        if status != "OK" or not messages[0]:
            print(f"No messages found in {mailbox}.")
            return

        # Create directory for this mailbox
        mailbox_dir = os.path.join(output_dir, sanitize_filename(mailbox))
        os.makedirs(mailbox_dir, exist_ok=True)

        # Process emails
        for num in messages[0].split():
            try:
                status, msg_data = mail.fetch(num, "(RFC822)")
                if status != "OK":
                    print(f"Failed to fetch message {num} in {mailbox}.")
                    continue

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1], policy=policy.default)
                        subject = msg.get("subject", "No_Subject")
                        filename = f"{num.decode('utf-8')}_{sanitize_filename(subject)}.eml"

                        with open(os.path.join(mailbox_dir, filename), "wb") as f:
                            f.write(response_part[1])
                        print(f"Saved: {mailbox}/{filename}")
            except Exception as e:
                print(f"Error processing email {num} in {mailbox}: {e}")

    except Exception as e:
        print(f"Error accessing mailbox {mailbox}: {e}")

def sanitize_filename(filename):
    """Sanitizes a string to be used as a filename."""
    return "".join(c if c.isalnum() else "_" for c in filename)

def main():
    # Get user inputs
    server, port, username, password = get_user_inputs()

    # Create output directory based on server and username
    output_dir = f"{sanitize_filename(server)}_{sanitize_filename(username)}"
    os.makedirs(output_dir, exist_ok=True)
    print(f"Emails will be saved in: {output_dir}")

    # Connect to IMAP server
    mail = connect_to_imap(server, port, username, password)
    if not mail:
        print("Exiting due to connection issues.")
        return

    # List and process mailboxes
    mailboxes = list_mailboxes(mail)
    if not mailboxes:
        print("No mailboxes found or unable to retrieve them.")
        return

    print(f"Found mailboxes: {mailboxes}")
    for mailbox in mailboxes:
        print(f"Processing mailbox: {mailbox}")
        download_emails(mail, mailbox, output_dir)

    # Logout
    try:
        mail.logout()
        print("Logged out successfully.")
    except Exception as e:
        print(f"Error during logout: {e}")

if __name__ == "__main__":
    main()
