library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity TopLevelAdapter is
port(
    clk : in std_logic;
    rst_n : in std_logic;
    RED : out std_logic_vector(5:0);
    HSYNC : out std_logic
);
end TopLevelAdapter;

architecture rtl of TopLevelAdapter is
    -- Internal Signals
    signal sig16 : STD_LOGIC;
    signal sig17 : STD_LOGIC;
    signal sig6 : STD_LOGIC;
    signal sig12 : STD_LOGIC_VECTOR(DATA_LEN - 1 downto 0);
    signal sig11 : STD_LOGIC_VECTOR(DATA_LEN - 1 downto 0);
    signal sig1 : STD_LOGIC;
    signal sig15 : STD_LOGIC;
    signal sig2 : STD_LOGIC;
    signal sig14 : STD_LOGIC;
    signal sig13 : STD_LOGIC;
    signal sig9 : integer;
    signal sig7 : STD_LOGIC;
    signal sig5 : STD_LOGIC;
    signal sig4 : STD_LOGIC_VECTOR(5 downto 0);
    signal sig10 : integer;
    signal sig8 : STD_LOGIC;
    signal sig3 : STD_LOGIC_VECTOR(5 downto 0);

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
    RGB666_Driver_inst : RGB666_Driver port map(
        CLK => clk,
        RESET_N => rst_n,
        HSYNC => HSYNC,
        VSYNC => sig1,
        DE => sig2,
        RED => RED,
        GREEN => sig3,
        BLUE => sig4,
        PCLK => sig5
    );

    spi9_inst : spi9 port map(
        CLK_1M => clk,
        RESET_N => rst_n,
        DAT_LOAD => sig5,
        LOAD_RDY => sig6,
        READ_RDY => sig7,
        SPI_MODE => sig8,
        DATA_WRITE_LEN => sig9,
        DATA_READ_LEN => sig10,
        DATA_IN => sig11,
        DATA_OUT => sig12,
        CS => sig13,
        SCL => sig14,
        SDA_IN => sig15,
        SDA_OUT => sig16,
        SDA_OE => sig17
    );

end rtl;
