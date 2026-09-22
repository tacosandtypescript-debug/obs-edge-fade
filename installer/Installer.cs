using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Reflection;
using System.Security.Principal;
using System.Text;
using System.Windows.Forms;

namespace ObsEdgeFadeSetup
{
    /// <summary>
    /// Installer for the OBS Edge Fade plugin.
    ///
    /// The plugin payload is embedded in this executable and extracted to the
    /// folder OBS reads plugins from, so there is nothing to copy by hand and no
    /// prerequisite beyond the .NET Framework that ships with Windows.
    ///
    /// Switches:
    ///   /silent      no window, exit code only
    ///   /uninstall   remove the plugin instead of installing it
    ///   /elevated    internal: set after a UAC relaunch to avoid looping
    /// </summary>
    internal static class Program
    {
        private const string PluginId = "obs-edge-fade";
        private const string DllRelativePath = @"bin\64bit\obs-edge-fade.dll";

        private static readonly string[] PayloadRelativePaths = Payload.RelativePaths;

        private static string Version
        {
            get { return Assembly.GetExecutingAssembly().GetName().Version.ToString(3); }
        }

        private static bool IsElevated()
        {
            using (WindowsIdentity identity = WindowsIdentity.GetCurrent())
            {
                return new WindowsPrincipal(identity).IsInRole(WindowsBuiltInRole.Administrator);
            }
        }

        /// <summary>Folders OBS loads plugins from, all-users first.</summary>
        private static IEnumerable<string> PluginRoots()
        {
            string programData = Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData);
            string appData = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);

            if (!string.IsNullOrEmpty(programData))
                yield return Path.Combine(programData, @"obs-studio\plugins");

            if (!string.IsNullOrEmpty(appData))
                yield return Path.Combine(appData, @"obs-studio\plugins");
        }

        private static string ObsExecutablePath()
        {
            foreach (string programFiles in new[]
                     {
                         Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),
                         Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86),
                     })
            {
                if (string.IsNullOrEmpty(programFiles))
                    continue;

                string candidate = Path.Combine(programFiles, @"obs-studio\bin\64bit\obs64.exe");
                if (File.Exists(candidate))
                    return candidate;
            }

            return null;
        }

        private static bool HasPermission(string directory)
        {
            try
            {
                string probe = Path.Combine(directory, ".oef-write-probe");
                File.WriteAllText(probe, "probe");
                File.Delete(probe);
                return true;
            }
            catch
            {
                return false;
            }
        }

        /// <summary>Pick the plugins folder to use, preferring an existing install.</summary>
        private static string ChooseTarget(out string reason)
        {
            List<string> roots = new List<string>(PluginRoots());

            // An existing installation wins, so re-running upgrades in place.
            foreach (string root in roots)
            {
                if (Directory.Exists(Path.Combine(root, PluginId)))
                {
                    reason = "upgrading the existing installation";
                    return Path.Combine(root, PluginId);
                }
            }

            foreach (string root in roots)
            {
                if (!Directory.Exists(root))
                    continue;

                if (HasPermission(root))
                {
                    reason = "OBS plugins folder";
                    return Path.Combine(root, PluginId);
                }
            }

            // Nothing usable found: create the all-users folder, which may need
            // elevation later.
            reason = "OBS plugins folder (will be created)";
            return Path.Combine(roots[0], PluginId);
        }

        /// <summary>Decodes one of the payload files baked in at build time.</summary>
        private static byte[] ReadPayload(int index)
        {
            return Convert.FromBase64String(Payload.Base64[index]);
        }

        internal static int Install(TextWriter log, bool silent)
        {
            log.WriteLine("OBS Edge Fade " + Version + " - installer");
            log.WriteLine();

            string obs = ObsExecutablePath();
            if (obs == null && !silent)
            {
                DialogResult answer = MessageBox.Show(
                    "OBS Studio was not found in the usual location.\r\n\r\n" +
                    "The plugin can still be installed, but make sure OBS is installed " +
                    "before using it.\r\n\r\nContinue?",
                    "OBS Edge Fade", MessageBoxButtons.YesNo, MessageBoxIcon.Warning);

                if (answer != DialogResult.Yes)
                    return 2;
            }
            else if (obs != null)
            {
                log.WriteLine("OBS found: " + obs);
            }

            string reason;
            string target = ChooseTarget(out reason);
            log.WriteLine("Target:   " + target + " (" + reason + ")");

            // Create and populate; a permission failure means we need elevation.
            try
            {
                Directory.CreateDirectory(Path.Combine(target, @"bin\64bit"));
                Directory.CreateDirectory(Path.Combine(target, @"data\effects"));
                Directory.CreateDirectory(Path.Combine(target, @"data\locale"));

                for (int index = 0; index < PayloadRelativePaths.Length; index++)
                {
                    string relative = PayloadRelativePaths[index];
                    byte[] bytes = ReadPayload(index);
                    string destination = Path.Combine(target, relative);

                    File.WriteAllBytes(destination, bytes);
                    log.WriteLine("  wrote " + relative + " (" + bytes.Length + " bytes)");
                }
            }
            catch (UnauthorizedAccessException)
            {
                log.WriteLine();
                log.WriteLine("No permission to write into that folder.");

                if (!IsElevated())
                {
                    log.WriteLine("Retrying with administrator rights...");
                    return RelaunchElevated(silent ? "/silent" : "");
                }

                log.WriteLine("Administrator rights were not enough. Aborting.");
                return 3;
            }
            catch (Exception exception)
            {
                log.WriteLine();
                log.WriteLine("Failed: " + exception.Message);
                return 3;
            }

            // Verify what we just wrote, byte for byte.
            for (int index = 0; index < PayloadRelativePaths.Length; index++)
            {
                string relative = PayloadRelativePaths[index];
                string destination = Path.Combine(target, relative);

                if (!File.Exists(destination))
                {
                    log.WriteLine("Verification failed: " + relative + " is missing");
                    return 4;
                }

                byte[] expected = ReadPayload(index);
                byte[] actual = File.ReadAllBytes(destination);

                if (expected.Length != actual.Length)
                {
                    log.WriteLine("Verification failed: " + relative + " has the wrong size");
                    return 4;
                }
            }

            log.WriteLine();
            log.WriteLine("Installed and verified.");

            string dll = Path.Combine(target, DllRelativePath);
            log.WriteLine("  " + dll);

            bool obsRunning = Process.GetProcessesByName("obs64").Length > 0;
            if (obsRunning)
            {
                log.WriteLine();
                log.WriteLine("OBS is running: it has to be restarted before the filter appears.");

                if (!silent)
                {
                    DialogResult restart = MessageBox.Show(
                        "Installed correctly.\r\n\r\n" +
                        "OBS is running and only loads plugins at startup. " +
                        "Close it now so the filter appears next time you open it?\r\n\r\n" +
                        "Save anything you are recording first.",
                        "OBS Edge Fade", MessageBoxButtons.YesNo, MessageBoxIcon.Information);

                    if (restart == DialogResult.Yes)
                        CloseObs(log);
                }
            }

            return 0;
        }

        internal static int Uninstall(TextWriter log, bool silent)
        {
            log.WriteLine("OBS Edge Fade " + Version + " - uninstaller");
            log.WriteLine();

            bool removedAnything = false;

            foreach (string root in PluginRoots())
            {
                string target = Path.Combine(root, PluginId);
                if (!Directory.Exists(target))
                    continue;

                try
                {
                    Directory.Delete(target, true);
                    log.WriteLine("  removed " + target);
                    removedAnything = true;
                }
                catch (UnauthorizedAccessException)
                {
                    if (!IsElevated())
                    {
                        log.WriteLine("Need administrator rights to remove " + target);
                        return RelaunchElevated("/uninstall" + (silent ? " /silent" : ""));
                    }

                    log.WriteLine("Could not remove " + target);
                    return 3;
                }
            }

            log.WriteLine();
            log.WriteLine(removedAnything
                ? "Removed. Restart OBS to finish."
                : "Nothing to remove: the plugin is not installed.");

            return removedAnything ? 0 : 1;
        }

        private static void CloseObs(TextWriter log)
        {
            foreach (Process process in Process.GetProcessesByName("obs64"))
            {
                try
                {
                    process.CloseMainWindow();
                    if (!process.WaitForExit(15000))
                        process.Kill();

                    log.WriteLine("  closed OBS (pid " + process.Id + ")");
                }
                catch (Exception exception)
                {
                    log.WriteLine("  could not close OBS: " + exception.Message);
                }
            }
        }

        /// <summary>Re-runs this executable elevated, which raises the UAC prompt.</summary>
        private static int RelaunchElevated(string extraArguments)
        {
            try
            {
                ProcessStartInfo start = new ProcessStartInfo
                {
                    FileName = Assembly.GetExecutingAssembly().Location,
                    Arguments = ("/elevated " + extraArguments).Trim(),
                    UseShellExecute = true,
                    Verb = "runas",
                };

                Process child = Process.Start(start);
                if (child == null)
                    return 3;

                child.WaitForExit();
                return child.ExitCode;
            }
            catch (Exception)
            {
                // The user declined the UAC prompt.
                return 5;
            }
        }

        [STAThread]
        private static int Main(string[] args)
        {
            bool silent = Array.Exists(args, a => a.Equals("/silent", StringComparison.OrdinalIgnoreCase));
            bool uninstall = Array.Exists(args, a => a.Equals("/uninstall", StringComparison.OrdinalIgnoreCase));

            if (silent)
            {
                using (StringWriter log = new StringWriter())
                {
                    int code = uninstall ? Uninstall(log, true) : Install(log, true);
                    if (code != 0)
                        Console.Error.WriteLine(log.ToString());

                    return code;
                }
            }

            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);

            using (SetupForm form = new SetupForm(uninstall))
            {
                Application.Run(form);
                return form.ExitCode;
            }
        }
    }

    /// <summary>Small native window that reports what the installer is doing.</summary>
    internal sealed class SetupForm : Form
    {
        private readonly bool _uninstall;
        private readonly TextBox _output;
        private readonly Button _action;
        private readonly Button _close;

        public int ExitCode { get; private set; }

        public SetupForm(bool uninstall)
        {
            _uninstall = uninstall;

            Text = "OBS Edge Fade " + Assembly.GetExecutingAssembly().GetName().Version.ToString(3) +
                   (uninstall ? " - uninstall" : " - setup");
            ClientSize = new Size(560, 320);
            MinimumSize = new Size(480, 260);
            StartPosition = FormStartPosition.CenterScreen;
            Font = new Font("Segoe UI", 9f);
            Icon = SystemIcons.Application;

            _output = new TextBox
            {
                Multiline = true,
                ReadOnly = true,
                ScrollBars = ScrollBars.Vertical,
                Dock = DockStyle.Fill,
                BackColor = SystemColors.Window,
                Font = new Font("Consolas", 9f),
            };

            Panel buttons = new Panel { Dock = DockStyle.Bottom, Height = 46 };

            _action = new Button
            {
                Text = uninstall ? "Desinstalar" : "Instalar",
                Width = 110,
                Height = 30,
                Left = buttons.Width - 240,
                Top = 8,
                Anchor = AnchorStyles.Right | AnchorStyles.Top,
            };
            _action.Click += OnAction;

            _close = new Button
            {
                Text = "Cerrar",
                Width = 110,
                Height = 30,
                Left = buttons.Width - 120,
                Top = 8,
                Anchor = AnchorStyles.Right | AnchorStyles.Top,
            };
            _close.Click += delegate { Close(); };

            buttons.Controls.Add(_action);
            buttons.Controls.Add(_close);
            buttons.Resize += delegate
            {
                _close.Left = buttons.Width - _close.Width - 12;
                _action.Left = _close.Left - _action.Width - 8;
            };

            Controls.Add(_output);
            Controls.Add(buttons);
        }

        private void OnAction(object sender, EventArgs eventArgs)
        {
            _action.Enabled = false;
            _output.Clear();

            using (StringWriter log = new StringWriter())
            {
                ExitCode = _uninstall
                    ? Program.Uninstall(log, false)
                    : Program.Install(log, false);

                // StringWriter already emits \r\n on Windows; normalise so the
                // text box never shows doubled line breaks.
                _output.Text = log.ToString().Replace("\r\n", "\n").Replace("\n", "\r\n");
                _output.SelectionStart = _output.TextLength;
                _output.ScrollToCaret();
            }

            _action.Text = "Repetir";
            _action.Enabled = true;
        }
    }
}



