from __future__ import print_function
from __future__ import unicode_literals
import time
import re
from netmiko.cisco_base_connection import CiscoSSHConnection
from netmiko import log


class HuaweiSSH(CiscoSSHConnection):
    def session_preparation(self):
        """Prepare the session after the connection has been established."""
        self._test_channel_read()
        self.set_base_prompt()
        self.disable_paging(command="screen-length 0 temporary")
        # Clear the read buffer
        time.sleep(0.3 * self.global_delay_factor)
        self.clear_buffer()

    def config_mode(self, config_command="system-view"):
        """Enter configuration mode."""
        return super(HuaweiSSH, self).config_mode(config_command=config_command)

    def exit_config_mode(self, exit_config="return", pattern=r">"):
        """Exit configuration mode."""
        return super(HuaweiSSH, self).exit_config_mode(
            exit_config=exit_config, pattern=pattern
        )

    def check_config_mode(self, check_string="]"):
        """Checks whether in configuration mode. Returns a boolean."""
        return super(HuaweiSSH, self).check_config_mode(check_string=check_string)

    def check_enable_mode(self, *args, **kwargs):
        """Huawei has no enable mode."""
        pass

    def enable(self, *args, **kwargs):
        """Huawei has no enable mode."""
        return ""

    def exit_enable_mode(self, *args, **kwargs):
        """Huawei has no enable mode."""
        return ""

    def set_base_prompt(
        self, pri_prompt_terminator=">", alt_prompt_terminator="]", delay_factor=1
    ):
        """
        Sets self.base_prompt

        Used as delimiter for stripping of trailing prompt in output.

        Should be set to something that is general and applies in multiple contexts. For Comware
        this will be the router prompt with < > or [ ] stripped off.

        This will be set on logging in, but not when entering system-view
        """
        log.debug("In set_base_prompt")
        delay_factor = self.select_delay_factor(delay_factor)
        self.clear_buffer()
        self.write_channel(self.RETURN)
        time.sleep(0.5 * delay_factor)

        prompt = self.read_channel()
        prompt = self.normalize_linefeeds(prompt)

        # If multiple lines in the output take the last line
        prompt = prompt.split(self.RESPONSE_RETURN)[-1]
        prompt = prompt.strip()

        # Check that ends with a valid terminator character
        if not prompt[-1] in (pri_prompt_terminator, alt_prompt_terminator):
            raise ValueError("Router prompt not found: {0}".format(prompt))

        # Strip off any leading HRP_. characters for USGv5 HA
        prompt = re.sub(r"^HRP_.", "", prompt, flags=re.M)

        # Strip off leading and trailing terminator
        prompt = prompt[1:-1]
        prompt = prompt.strip()
        self.base_prompt = prompt
        log.debug("prompt: {0}".format(self.base_prompt))

        return self.base_prompt

    def save_config(self, cmd="save", confirm=True, confirm_response="Y"):
        """ Save Config for HuaweiSSH"""
        return super(HuaweiSSH, self).save_config(cmd=cmd, confirm=confirm, confirm_response=confirm_response)
        
        
    def serial_login(
        self,
        pri_prompt_terminator=r">\s*$",
        alt_prompt_terminator=r"]\s*$",
        username_pattern=r"(?:user:|username|login)",
        pwd_pattern=r"assword",
        delay_factor=1,
        max_loops=20,
    ):
        self.write_channel(self.TELNET_RETURN)
        output = self.read_channel()
        if re.search(r"Continue to set it? \[Y/N\]:",output):
            self.write_channel("N" + self.TELNET_RETURN)
        if re.search(pri_prompt_terminator, output, flags=re.M) or re.search(
            alt_prompt_terminator, output, flags=re.M
        ):
            return output
        else:
            return self.telnet_login(
                pri_prompt_terminator,
                alt_prompt_terminator,
                username_pattern,
                pwd_pattern,
                delay_factor,
                max_loops,
            )


class HuaweiTelnet(HuaweiSSH):
    pass


class HuaweiSerial(HuaweiSSH):
    pass


class HuaweiVrpv8SSH(HuaweiSSH):
    def commit(self, comment="", delay_factor=1):
        """
        Commit the candidate configuration.

        Commit the entered configuration. Raise an error and return the failure
        if the commit fails.

        default:
           command_string = commit
        comment:
           command_string = commit comment <comment>

        """
        delay_factor = self.select_delay_factor(delay_factor)
        error_marker = "Failed to generate committed config"
        command_string = "commit"

        if comment:
            command_string += ' comment "{}"'.format(comment)

        output = self.config_mode()
        output += self.send_command_expect(
            command_string,
            strip_prompt=False,
            strip_command=False,
            delay_factor=delay_factor,
            expect_string=r"]",
        )
        output += self.exit_config_mode()

        if error_marker in output:
            raise ValueError(
                "Commit failed with following errors:\n\n{}".format(output)
            )
        return output

    def save_config(self, cmd="", confirm=True, confirm_response=""):
        """Not Implemented"""
        raise NotImplementedError
