library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity TopLevelAdapter is
port(
    clk : in std_logic;
    HSYNC : out STD_LOGIC;
    VSYNC : out STD_LOGIC;
    DE : out STD_LOGIC;
    RED : out STD_LOGIC_VECTOR(5 downto 0);
    GREEN : out STD_LOGIC_VECTOR(5 downto 0);
    BLUE : out STD_LOGIC_VECTOR(5 downto 0);
    PCLK : out STD_LOGIC
);
end TopLevelAdapter;

architecture rtl of TopLevelAdapter is
    -- Internal Signals
    signal sig1 : STD_LOGIC;

    component RGB666_Driver is
    generic(
        WIDTH : integer := 400;
        HEIGHT : integer := 960;
        FPS : integer := 60;
        CLK_FREQ : integer := 50000000;
        PORCH_CNT : integer := 3
    );
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
    RGB666_Driver_inst : RGB666_Driver generic map(
        WIDTH => 400,
        HEIGHT => 960,
        FPS => 60,
        CLK_FREQ => 50000000,
        PORCH_CNT => 3
    ) port map(
        CLK => clk,
        RESET_N => sig1,
        HSYNC => HSYNC,
        VSYNC => VSYNC,
        DE => DE,
        RED => RED,
        GREEN => GREEN,
        BLUE => BLUE,
        PCLK => PCLK
    );

end rtl;
