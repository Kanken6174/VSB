library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity TopLevelAdapter is
port(
    sig : out std_logic
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

begin
    RGB666_Driver_inst : RGB666_Driver port map(
        CLK => sig,
        RESET_N => '0',
        HSYNC => open,
        VSYNC => open,
        DE => open,
        RED => open,
        GREEN => open,
        BLUE => open,
        PCLK => open
    );

end rtl;
