library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity TopLevelAdapter is
port(
    clk : in std_logic;
    hsync : out std_logic
);
end TopLevelAdapter;

architecture rtl of TopLevelAdapter is
    -- Internal Signals
    signal sig2 : STD_LOGIC;
    signal sig1 : STD_LOGIC;
    signal sig4 : STD_LOGIC_VECTOR(5 downto 0);
    signal sig6 : STD_LOGIC_VECTOR(5 downto 0);
    signal sig7 : STD_LOGIC;
    signal sig5 : STD_LOGIC_VECTOR(5 downto 0);
    signal sig3 : STD_LOGIC;

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

begin
    RGB666_Driver_inst : RGB666_Driver port map(
        CLK => clk,
        RESET_N => sig1,
        HSYNC => hsync,
        VSYNC => sig2,
        DE => sig3,
        RED => sig4,
        GREEN => sig5,
        BLUE => sig6,
        PCLK => sig7
    );

end rtl;
