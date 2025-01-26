library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
entity TopLevelAdapter is
port(
clk : out std_logic;
rst_n : out std_logic
);
end TopLevelAdapter;
architecture rtl of TopLevelAdapter is
component RGB666_Driver is
port(
CLK : in STD_LOGIC;
RESET_N : in STD_LOGIC;
HSYNC : out STD_LOGIC;
VSYNC : out STD_LOGIC;
DE : out STD_LOGIC;
RED : out STD_LOGIC_VECTOR(5 downto 0);
GREEN : out STD_LOGIC_VECTOR(5 downto 0);
BLUE : out STD_LOGIC_VECTOR(5 downto 0);
PCLK : out STD_LOGIC
);
end component;
component spi9 is
port(
CLK_1M : in STD_LOGIC;
RESET_N : in STD_LOGIC;
DAT_LOAD : in STD_LOGIC;
LOAD_RDY : out STD_LOGIC;
READ_RDY : out STD_LOGIC;
SPI_MODE : in STD_LOGIC;
DATA_WRITE_LEN : in integer;
DATA_READ_LEN : in integer;
DATA_IN : in STD_LOGIC_VECTOR(DATA_LEN - 1 downto 0);
DATA_OUT : out STD_LOGIC_VECTOR(DATA_LEN - 1 downto 0);
CS : out STD_LOGIC;
SCL : out STD_LOGIC;
SDA_IN : in STD_LOGIC;
SDA_OUT : out STD_LOGIC;
SDA_OE : out STD_LOGIC
);
end component;
begin
RGB666_Driver_inst0: RGB666_Driver port map(
);
spi9_inst0: spi9 port map(
);
end rtl;