This is a simple python tool to create SOCs for efinix fpga projects (though it may work for other platforms), it only supports VHDL as a language and relies on VHDL regex parsing to actually detect and create IP blocks/templates.

Note:
anything called `tb_<something>.vhd` or `<something>_tb.vhd` will be ignored as a GHDL test bench
anything called `<something>_tmpl.vhd` will be treated as an efinix instantiation template

This software excepects the following structure:
```yaml
selected project root/
                      X.vhd(l)
                      ip/*/
                      otherIps.vhd(l)
```
